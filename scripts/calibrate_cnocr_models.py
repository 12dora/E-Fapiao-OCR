"""Run local CnOCR model calibration against sample invoices.

Outputs are intentionally written under docs/sample/, which is gitignored because
the OCR text can contain real invoice data.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium  # type: ignore[import-untyped]
from cnocr import CnOcr  # type: ignore[import-not-found]

from app.core import detector, normalizer
from app.extractors.version_adapter import select_extractor
from app.ocr.base import OcrResult, OcrTextLine
from app.ocr.vendors.cnocr_vendor import _to_text_line
from app.ocr.vendors.tencent_vendor import _parse_response

DEFAULT_MODELS = [
    "doc-densenet_lite_136-gru",
    "densenet_lite_136-gru",
    "scene-densenet_lite_136-gru",
    "ch_ppocr_mobile_v2.0",
]


@dataclass(frozen=True)
class ModelSpec:
    rec_model: str
    rec_backend: str = "onnx"
    det_model: str = "ch_PP-OCRv5_det"
    det_backend: str = "onnx"

    @property
    def slug(self) -> str:
        return (
            f"det-{self.det_model}-{self.det_backend}"
            f"__rec-{self.rec_model}-{self.rec_backend}"
        ).replace("/", "_")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-dir", default="docs/sample")
    parser.add_argument(
        "--tencent-dir",
        default="docs/sample/tencent-ocr-calibration-20260522-100154",
    )
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    sample_dir = Path(args.sample_dir)
    tencent_dir = Path(args.tencent_dir)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = Path(args.output_dir or sample_dir / f"cnocr-model-calibration-{run_id}")
    output_dir.mkdir(parents=True, exist_ok=True)

    files = _sample_files(sample_dir, tencent_dir)
    if args.limit:
        files = files[: args.limit]

    all_summaries: list[dict[str, Any]] = []
    for rec_model in args.models:
        spec = ModelSpec(rec_model=rec_model)
        summary = _run_model(spec, files, sample_dir, tencent_dir, output_dir)
        all_summaries.append(summary)

    comparison = {
        "run_id": run_id,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "sample_dir": str(sample_dir),
        "tencent_dir": str(tencent_dir),
        "output_dir": str(output_dir),
        "models": all_summaries,
    }
    (output_dir / "comparison_summary.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(comparison, ensure_ascii=False, indent=2))
    return 0


def _sample_files(sample_dir: Path, tencent_dir: Path) -> list[str]:
    summary = json.loads((tencent_dir / "summary.json").read_text(encoding="utf-8"))
    return [
        item["file"]
        for item in summary["files"]
        if (sample_dir / item["file"]).suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg"}
    ]


def _run_model(
    spec: ModelSpec,
    files: list[str],
    sample_dir: Path,
    tencent_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    model_dir = output_dir / spec.slug
    raw_dir = model_dir / "raw"
    text_dir = model_dir / "text"
    parsed_dir = model_dir / "parsed"
    for path in (raw_dir, text_dir, parsed_dir):
        path.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    ocr = CnOcr(
        det_model_name=spec.det_model,
        rec_model_name=spec.rec_model,
        det_model_backend=spec.det_backend,
        rec_model_backend=spec.rec_backend,
    )

    records: list[dict[str, Any]] = []
    for file in files:
        record = _run_file(spec, ocr, sample_dir / file, tencent_dir, raw_dir, text_dir, parsed_dir)
        records.append(record)
        print(
            spec.rec_model,
            file,
            "ok" if record["ok"] else record.get("error_type"),
            record["elapsed_seconds"],
        )

    summary = _summarize(spec, records, time.perf_counter() - started)
    (model_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def _run_file(
    spec: ModelSpec,
    ocr: CnOcr,
    sample_path: Path,
    tencent_dir: Path,
    raw_dir: Path,
    text_dir: Path,
    parsed_dir: Path,
) -> dict[str, Any]:
    started = time.perf_counter()
    stem = sample_path.stem
    record: dict[str, Any] = {
        "file": sample_path.name,
        "model": spec.rec_model,
        "det_model": spec.det_model,
        "ok": False,
    }
    try:
        result = _recognize_path(ocr, sample_path)
        raw_payload = {
            "file": sample_path.name,
            "model": spec.__dict__,
            "lines": [
                {"text": line.text, "score": line.score, "bbox": line.bbox}
                for line in result.lines
            ],
        }
        (raw_dir / f"{stem}.json").write_text(
            json.dumps(raw_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (text_dir / f"{stem}.txt").write_text(result.text, encoding="utf-8")

        record.update(
            {
                "recognize_ok": True,
                "line_count": len(result.lines),
                "char_count": len(result.text),
                "raw_file": f"raw/{stem}.json",
                "text_file": f"text/{stem}.txt",
            }
        )
        parsed, parse_error = _try_parse_ocr_text(
            sample_path,
            result.text,
            spec.rec_model,
            sample_path.read_bytes(),
        )
        if parsed:
            (parsed_dir / f"{stem}.json").write_text(
                json.dumps(parsed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            record["parsed_file"] = f"parsed/{stem}.json"

        expected = _expected_from_tencent(tencent_dir, stem, sample_path.suffix.lower())
        record.update(
            {
                "ok": True,
                "parse_ok": parsed is not None,
                "parse_error": parse_error,
                "expected_parse_ok": expected is not None,
                "matches": _field_matches(parsed, expected) if parsed and expected else {},
                "parsed_invoice_type": parsed.get("invoice_type") if parsed else None,
                "expected_invoice_type": expected.get("invoice_type"),
            }
        )
    except Exception as e:
        record.update({"error_type": type(e).__name__, "error": str(e)})
    finally:
        record["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    return record


def _recognize_path(ocr: CnOcr, path: Path) -> OcrResult:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _recognize_pdf(ocr, path)
    raw_items = ocr.ocr(path)
    return _ocr_result(raw_items)


def _recognize_pdf(ocr: CnOcr, path: Path) -> OcrResult:
    pdf = pdfium.PdfDocument(BytesIO(path.read_bytes()))
    try:
        lines: list[OcrTextLine] = []
        for page in pdf:
            image = page.render(scale=200 / 72).to_pil()
            page.close()
            lines.extend(_ocr_result(ocr.ocr(image)).lines)
        return OcrResult(lines=lines, vendor="cnocr")
    finally:
        pdf.close()


def _ocr_result(items: list[dict[str, Any]]) -> OcrResult:
    lines = [_to_text_line(item) for item in items]
    return OcrResult(lines=[line for line in lines if line.text], vendor="cnocr")


def _try_parse_ocr_text(
    path: Path,
    text: str,
    model_name: str,
    content: bytes | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return _parse_ocr_text(path, text, model_name, content), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _parse_ocr_text(
    path: Path,
    text: str,
    model_name: str,
    content: bytes | None = None,
) -> dict[str, Any]:
    raw = select_extractor(text)(text)
    raw.setdefault("source", {})
    raw["source"]["format"] = detector.detect(content or b"", path.name)
    raw["source"]["extracted_by"] = "ocr"
    raw["source"]["ocr_vendor"] = f"cnocr:{model_name}"
    return normalizer.normalize(raw)


def _expected_from_tencent(tencent_dir: Path, stem: str, suffix: str) -> dict[str, Any]:
    raw = json.loads((tencent_dir / "raw" / f"{stem}.json").read_text(encoding="utf-8"))
    result = _parse_response(raw["response"])
    parsed = _parse_ocr_text(Path(f"{stem}{suffix}"), result.text, "tencent-calibration")
    parsed["source"]["ocr_vendor"] = "tencent"
    return parsed


def _field_matches(parsed: dict[str, Any], expected: dict[str, Any]) -> dict[str, bool]:
    fields = [
        "document_type",
        "invoice_type",
        "invoice_number",
        "invoice_code",
        "issue_date",
        "amount_without_tax",
        "tax_amount",
        "amount_with_tax",
    ]
    matches = {field: parsed.get(field) == expected.get(field) for field in fields}
    for party in ("buyer", "seller"):
        for field in ("name", "tax_id"):
            key = f"{party}.{field}"
            matches[key] = parsed.get(party, {}).get(field) == expected.get(party, {}).get(field)
    return matches


def _summarize(spec: ModelSpec, records: list[dict[str, Any]], elapsed: float) -> dict[str, Any]:
    ok_records = [record for record in records if record["ok"]]
    parse_ok_records = [record for record in ok_records if record.get("parse_ok")]
    field_totals: dict[str, int] = {}
    for record in parse_ok_records:
        for field, matched in record.get("matches", {}).items():
            field_totals.setdefault(field, 0)
            if matched:
                field_totals[field] += 1
    return {
        "model": spec.rec_model,
        "det_model": spec.det_model,
        "rec_backend": spec.rec_backend,
        "det_backend": spec.det_backend,
        "total": len(records),
        "ok": len(ok_records),
        "failed": len(records) - len(ok_records),
        "parse_ok": len(parse_ok_records),
        "parse_failed": len(ok_records) - len(parse_ok_records),
        "elapsed_seconds": round(elapsed, 3),
        "avg_elapsed_seconds": round(
            sum(r["elapsed_seconds"] for r in records) / max(len(records), 1),
            3,
        ),
        "field_match_counts": field_totals,
        "records": records,
    }


if __name__ == "__main__":
    raise SystemExit(main())
