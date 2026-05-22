"""Generate sanitized regression fixtures from local real invoice samples.

The output is safe to commit: raw documents are never copied, and all known
identifiers, names, dates, and monetary values are replaced with deterministic
synthetic values while preserving layout-oriented text shape.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from statistics import median
from typing import Any

from PIL import Image

from app.core import normalizer
from app.extractors import air_itinerary
from app.extractors.version_adapter import select_extractor
from app.ocr.vendors.tencent_vendor import _parse_response
from app.parsers.ofd_parser import _extract_ofd_package
from app.parsers.pdf_parser import PdfParser

DEFAULT_SAMPLE_DIR = Path("docs/sample")
DEFAULT_TENCENT_DIR = Path("docs/sample/tencent-ocr-calibration-20260522-100154")
DEFAULT_OUTPUT = Path("tests/fixtures/sanitized_regression_cases.json")

COMPANY_TAIL = (
    "有限公司",
    "股份有限公司",
    "分公司",
    "餐饮店",
    "商店",
    "中心",
    "酒店",
    "医院",
    "学校",
)
SENSITIVE_KEYS = {
    "Buyer",
    "Seller",
    "BuyerTaxID",
    "SellerTaxID",
    "UserName",
    "UserID",
    "Issuer",
    "Receiptor",
    "Reviewer",
    "ElectronicTicketNum",
    "VerificationCode",
    "CheckCode",
    "Ciphertext",
    "CompanySealContent",
    "TaxSealContent",
    "SellerAddrTel",
    "SellerBankAccount",
    "CutImage",
    "Number",
    "Code",
    "MachineCode",
    "QRCode",
    "RequestId",
}


@dataclass
class Sanitizer:
    mappings: dict[str, str] = field(default_factory=dict)
    counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    case_index: int = 0

    def sanitize_tree(self, value: Any, key: str = "") -> Any:
        if isinstance(value, dict):
            return {k: self.sanitize_tree(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [self.sanitize_tree(item, key) for item in value]
        if isinstance(value, str):
            return self.sanitize_string(value, key)
        return value

    def sanitize_string(self, value: str, key: str = "") -> str:
        if value in {"", "OK"}:
            return value
        if key == "CutImage":
            return ""
        if key == "QRCode":
            return self._stable_token(value, "qrcode")
        if key == "RequestId":
            return self._stable_token(value, "request")
        text = value
        for raw, replacement in sorted(
            self.mappings.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            if raw:
                text = text.replace(raw, replacement)

        if key in {"Date", "DateGetOn", "IssueDate"}:
            text = self._date_value(text)
        if key in {"TotalCn", "amount_in_words"}:
            text = "壹佰圆整"

        text = _DATE_RE.sub(lambda _: self._next_date(), text)
        text = _DATE_COMPACT_RE.sub(lambda _: self._next_compact_date(), text)
        text = _ID_MASK_RE.sub("110000********0001", text)
        text = _TAX_ID_RE.sub(lambda m: self._stable_token(m.group(0), "tax"), text)
        text = _LONG_NUMBER_RE.sub(lambda m: self._number_like(m.group(0), key), text)
        text = _MONEY_RE.sub(lambda m: f"{m.group(1) or ''}{self._money(m.group(2))}", text)
        text = _CNY_MONEY_RE.sub(lambda m: f"{m.group(1)} {self._money(m.group(2))}", text)
        text = _COMPANY_RE.sub(lambda m: self._stable_token(m.group(0), "company"), text)
        return text

    def collect_sensitive_values(self, value: Any, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                self.collect_sensitive_values(child_value, child_key)
            return
        if isinstance(value, list):
            for item in value:
                self.collect_sensitive_values(item, key)
            return
        if not isinstance(value, str) or not value.strip():
            return

        raw = value.strip()
        if key in SENSITIVE_KEYS and key != "Code":
            self._map_value(raw, _category_for_key(key))
        for company in _COMPANY_RE.findall(raw):
            self._map_value(company, "company")

    def _map_value(self, raw: str, category: str) -> None:
        if raw in {"OK"} or len(raw) <= 1:
            return
        if raw not in self.mappings:
            self.mappings[raw] = self._next_value(category, raw)

    def _stable_token(self, raw: str, category: str) -> str:
        if raw not in self.mappings:
            self._map_value(raw, category)
        return self.mappings[raw]

    def _next_value(self, category: str, raw: str) -> str:
        self.counters[category] += 1
        idx = self.counters[category]
        if category == "company":
            tail = "有限公司"
            for candidate in COMPANY_TAIL:
                if raw.endswith(candidate):
                    tail = candidate
                    break
            return f"脱敏主体{idx:03d}{tail}"
        if category == "person":
            return f"测试人员{idx:03d}"
        if category == "tax":
            return f"911100000000{idx:04d}A"[-18:]
        if category == "id":
            return "110000********0001"
        if category == "ticket":
            return f"78123456{idx:05d}"
        if category == "code":
            return f"{idx:020d}"
        if category == "qrcode":
            return f"QR,SANITIZED,{idx:06d}"
        if category == "request":
            return f"00000000-0000-4000-8000-{idx:012d}"
        return f"脱敏值{idx:03d}"

    def _number_like(self, raw: str, key: str) -> str:
        category = "ticket" if "Ticket" in key else "code"
        synthetic = self._stable_token(raw, category)
        if len(synthetic) < len(raw):
            synthetic = synthetic.zfill(len(raw))
        return synthetic[-len(raw) :]

    def _money(self, raw: str) -> str:
        key = f"money:{raw}"
        if key not in self.mappings:
            self.counters["money"] += 1
            value = Decimal("100.00") + Decimal(self.counters["money"]) * Decimal("7.13")
            self.mappings[key] = f"{value:.2f}"
        return self.mappings[key]

    def _next_date(self) -> str:
        self.counters["date"] += 1
        day = ((self.counters["date"] - 1) % 28) + 1
        return f"2026年01月{day:02d}日"

    def _next_compact_date(self) -> str:
        self.counters["date"] += 1
        day = ((self.counters["date"] - 1) % 28) + 1
        return f"202601{day:02d}"

    def _date_value(self, raw: str) -> str:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            self.counters["date"] += 1
            day = ((self.counters["date"] - 1) % 28) + 1
            return f"2026-01-{day:02d}"
        return self.sanitize_string(raw)


_DATE_RE = re.compile(r"(?:20\d{2})\s*[年/-]\s*\d{1,2}\s*[月/-]\s*\d{1,2}\s*日?")
_DATE_COMPACT_RE = re.compile(r"(?<!\d)20\d{6}(?!\d)")
_ID_MASK_RE = re.compile(r"\d{6}\*{4,}\d{4}|\d{6}\d{4}\*{4,}\d{4}")
_TAX_ID_RE = re.compile(r"\b[0-9A-Z]{15,20}\b")
_LONG_NUMBER_RE = re.compile(r"(?<![\d.])\d{8,24}(?![\d.])")
_MONEY_RE = re.compile(r"([¥￥Y])\s*(-?\d+\.\s*\d{1,2})")
_CNY_MONEY_RE = re.compile(r"\b(CNY)\s+(-?\d+\.\d{1,2})")
_COMPANY_RE = re.compile(
    r"[\u4e00-\u9fffA-Za-z0-9()（）]{2,40}(?:"
    + "|".join(re.escape(tail) for tail in COMPANY_TAIL)
    + r")"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-dir", type=Path, default=DEFAULT_SAMPLE_DIR)
    parser.add_argument("--tencent-dir", type=Path, default=DEFAULT_TENCENT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = build_fixture(args.sample_dir, args.tencent_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.output} ({len(payload['cases'])} cases)")
    return 0


def build_fixture(sample_dir: Path, tencent_dir: Path) -> dict[str, Any]:
    summary = json.loads((tencent_dir / "summary.json").read_text(encoding="utf-8"))
    files = summary["files"]
    sanitizer = Sanitizer()

    raw_responses = {}
    for item in files:
        raw = json.loads((tencent_dir / item["raw_file"]).read_text(encoding="utf-8"))
        response = raw["response"]
        raw_responses[item["file"]] = response
        sanitizer.collect_sensitive_values(response)

    cases = []
    for idx, item in enumerate(files, start=1):
        sanitizer.case_index = idx
        path = sample_dir / item["file"]
        content = path.read_bytes()
        raw_response = raw_responses[item["file"]]
        sanitized_response = sanitizer.sanitize_tree(raw_response)
        tencent_text = _parse_response(sanitized_response).text

        rule_input = _build_rule_input(path, content, sanitizer)
        cases.append(
            {
                "id": f"case_{idx:03d}_{path.stem}",
                "file_name": path.name,
                "source_format": path.suffix.lower().lstrip("."),
                "tencent_subtype": sanitizer.sanitize_string(item.get("tencent_subtype") or ""),
                "rule": rule_input,
                "visual": _build_visual_input(
                    path,
                    content,
                    sanitizer,
                    sanitized_response,
                    tencent_text,
                ),
                "tencent": {
                    "response": sanitized_response,
                    "ocr_text": tencent_text,
                    "expected": _try_parse_text(
                        tencent_text,
                        path.suffix.lower().lstrip("."),
                        extracted_by="ocr",
                        ocr_vendor="tencent",
                    ),
                },
            }
        )

    return {
        "version": 1,
        "source": "local real invoice samples + Tencent OCR calibration, sanitized",
        "case_count": len(cases),
        "sanitization": {
            "raw_documents": "not included",
            "identifiers": "deterministically replaced",
            "names": "deterministically replaced",
            "dates": "synthetic 2026-01-DD values",
            "amounts": "synthetic decimal values",
        },
        "cases": cases,
    }


def _build_rule_input(path: Path, content: bytes, sanitizer: Sanitizer) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            text = PdfParser._extract_text(content)
        except Exception as e:
            return {"kind": "pdf_text", "status": "error", "error": f"{type(e).__name__}: {e}"}
        sanitized_text = sanitizer.sanitize_string(text)
        return {
            "kind": "pdf_text",
            "text": sanitized_text,
            "expected": _try_parse_text(sanitized_text, "pdf"),
        }

    if suffix == ".ofd":
        try:
            package = _extract_ofd_package(content)
        except Exception as e:
            return {"kind": "ofd_fields", "status": "error", "error": f"{type(e).__name__}: {e}"}
        fields = sanitizer.sanitize_tree(package.fields)
        text = sanitizer.sanitize_string(
            "\n".join(text for _, _, text in [*package.template_text, *package.page_text])
        )
        return {
            "kind": "ofd_fields",
            "fields": fields,
            "page_text": text,
            "expected": _try_parse_ofd_fields(fields),
        }

    return {"kind": "image", "expected": {"status": "not_applicable"}}


def _build_visual_input(
    path: Path,
    content: bytes,
    sanitizer: Sanitizer,
    sanitized_response: dict[str, Any],
    tencent_text: str,
) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _build_pdf_text_layout(content, sanitizer)
    if suffix in {".png", ".jpg", ".jpeg"}:
        return _build_image_text_layout(content, sanitized_response, tencent_text)
    if suffix == ".ofd":
        return {
            "kind": "semantic_text",
            "source_format": "ofd",
            "text": sanitizer.sanitize_string(tencent_text),
        }
    return {"kind": "unsupported"}


def _build_pdf_text_layout(content: bytes, sanitizer: Sanitizer) -> dict[str, Any]:
    try:
        import pypdfium2 as pdfium  # type: ignore[import-untyped]

        pdf = pdfium.PdfDocument(content)
        try:
            pages = []
            for page_number, page in enumerate(pdf, start=1):
                width, height = page.get_size()
                textpage = page.get_textpage()
                try:
                    lines = _pdf_text_lines(textpage, sanitizer)
                finally:
                    textpage.close()
                pages.append(
                    {
                        "page": page_number,
                        "width_pt": round(float(width), 2),
                        "height_pt": round(float(height), 2),
                        "lines": lines,
                    }
                )
            return {
                "kind": "pdf_text_layout",
                "source_format": "pdf",
                "coordinate_system": "pdf_points_bottom_left",
                "pages": pages,
            }
        finally:
            pdf.close()
    except Exception as e:
        return {"kind": "pdf_text_layout", "status": "error", "error": f"{type(e).__name__}: {e}"}


def _pdf_text_lines(textpage: Any, sanitizer: Sanitizer) -> list[dict[str, Any]]:
    count = textpage.count_chars()
    lines: list[dict[str, Any]] = []
    chars: list[str] = []
    boxes: list[tuple[float, float, float, float]] = []

    def flush() -> None:
        raw_text = "".join(chars).strip()
        visible_boxes = [box for box in boxes if box[2] > box[0] and box[3] > box[1]]
        chars.clear()
        boxes.clear()
        if not raw_text or not visible_boxes:
            return
        left = min(box[0] for box in visible_boxes)
        bottom = min(box[1] for box in visible_boxes)
        right = max(box[2] for box in visible_boxes)
        top = max(box[3] for box in visible_boxes)
        heights = [box[3] - box[1] for box in visible_boxes if box[3] > box[1]]
        text = sanitizer.sanitize_string(raw_text)
        if not text:
            return
        lines.append(
            {
                "text": text,
                "bbox": [
                    round(float(left), 2),
                    round(float(bottom), 2),
                    round(float(right), 2),
                    round(float(top), 2),
                ],
                "font_size_pt": round(float(median(heights) if heights else top - bottom), 2),
            }
        )

    for index in range(count):
        char = textpage.get_text_range(index, 1)
        if char in {"\r", "\n"}:
            flush()
            continue
        chars.append(char)
        if char.strip():
            boxes.append(textpage.get_charbox(index))
    flush()
    return lines


def _build_image_text_layout(
    content: bytes,
    sanitized_response: dict[str, Any],
    tencent_text: str,
) -> dict[str, Any]:
    try:
        with Image.open(BytesIO(content)) as image:
            width_px, height_px = image.size
    except Exception:
        width_px, height_px = 1200, 800

    polygon = _first_invoice_polygon(sanitized_response)
    if polygon:
        left, top, right, bottom = polygon
    else:
        left, top, right, bottom = 40, 40, max(width_px - 40, 80), max(height_px - 40, 80)

    lines = [line.strip() for line in tencent_text.splitlines() if line.strip()]
    row_height = max(18, int((bottom - top) / max(len(lines), 1)))
    visual_lines = []
    for offset, line in enumerate(lines):
        y1 = top + offset * row_height
        y2 = min(y1 + row_height - 2, bottom)
        if y2 <= y1:
            break
        visual_lines.append(
            {
                "text": line,
                "bbox": [left, y1, right, y2],
                "font_size_px": max(12, min(24, row_height - 4)),
            }
        )

    return {
        "kind": "image_text_layout",
        "source_format": "image",
        "width_px": width_px,
        "height_px": height_px,
        "coordinate_system": "pixels_top_left",
        "lines": visual_lines,
    }


def _first_invoice_polygon(response: dict[str, Any]) -> tuple[int, int, int, int] | None:
    items = response.get("Response", {}).get("MixedInvoiceItems")
    if not isinstance(items, list) or not items:
        return None
    polygon = items[0].get("Polygon") if isinstance(items[0], dict) else None
    if not isinstance(polygon, dict):
        return None
    points = [value for value in polygon.values() if isinstance(value, dict)]
    xs = [int(point["X"]) for point in points if isinstance(point.get("X"), (int, float))]
    ys = [int(point["Y"]) for point in points if isinstance(point.get("Y"), (int, float))]
    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _try_parse_text(
    text: str,
    source_format: str,
    *,
    extracted_by: str = "text_layer",
    ocr_vendor: str | None = None,
) -> dict[str, Any]:
    try:
        raw = select_extractor(text)(text)
        raw.setdefault("source", {})["format"] = (
            "image" if source_format in {"png", "jpg", "jpeg"} else source_format
        )
        raw["source"]["extracted_by"] = extracted_by
        raw["source"]["ocr_vendor"] = ocr_vendor
        return {"status": "ok", "data": normalizer.normalize(raw)}
    except Exception as e:
        return {"status": "error", "error_type": type(e).__name__, "message": str(e)}


def _try_parse_ofd_fields(fields: dict[str, str]) -> dict[str, Any]:
    try:
        if fields.get("ElectronicInvoiceAirTransportReceiptNumber"):
            raw = air_itinerary.extract(fields)
            raw.setdefault("source", {})["format"] = "ofd"
            return {"status": "ok", "data": normalizer.normalize(raw)}
        return {"status": "unsupported"}
    except Exception as e:
        return {"status": "error", "error_type": type(e).__name__, "message": str(e)}


def _category_for_key(key: str) -> str:
    if key == "QRCode":
        return "qrcode"
    if key == "RequestId":
        return "request"
    if key in {"Buyer", "Seller", "CompanySealContent", "TaxSealContent", "SellerAddrTel"}:
        return "company"
    if key in {"UserName", "Issuer", "Receiptor", "Reviewer"}:
        return "person"
    if key == "UserID":
        return "id"
    if key == "ElectronicTicketNum":
        return "ticket"
    if key.endswith("TaxID"):
        return "tax"
    return "code"


if __name__ == "__main__":
    raise SystemExit(main())
