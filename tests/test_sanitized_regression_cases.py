"""Regression tests generated from sanitized real-sample abstractions.

The fixture deliberately contains no raw PDFs/OFDs/images. PDF cases preserve
text-layer layout after deterministic sanitization; Tencent cases preserve the
provider response shape after deterministic sanitization.
"""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from app.core.normalizer import normalize
from app.errors import ParseFailed, UnsupportedDocumentType
from app.extractors import air_itinerary
from app.extractors.version_adapter import select_extractor
from app.ocr.vendors.tencent_vendor import _parse_response
from tests.fixtures.sanitized_visual import render_visual_pdf, render_visual_png

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sanitized_regression_cases.json"


def _cases() -> list[dict[str, Any]]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]


CASES = _cases()


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_rule_engine_sanitized_real_sample_abstractions(case: dict[str, Any]) -> None:
    rule = case["rule"]
    expected = rule.get("expected", {})
    if expected.get("status") == "not_applicable":
        pytest.skip("image sample has no rule-engine text abstraction")
    if expected.get("status") != "ok":
        with pytest.raises((ParseFailed, NotImplementedError, UnsupportedDocumentType)):
            _parse_rule_input(rule, case["source_format"])
        return

    assert _parse_rule_input(rule, case["source_format"]) == expected["data"]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_tencent_sanitized_real_sample_responses(case: dict[str, Any]) -> None:
    expected = case["tencent"]["expected"]
    assert expected["status"] == "ok"

    result = _parse_response(case["tencent"]["response"])
    raw = select_extractor(result.text)(result.text)
    raw.setdefault("source", {})["format"] = (
        "image" if case["source_format"] in {"png", "jpg", "jpeg"} else case["source_format"]
    )
    raw["source"]["extracted_by"] = "ocr"
    raw["source"]["ocr_vendor"] = "tencent"

    assert normalize(raw) == expected["data"]


def test_sanitized_regression_fixture_has_100_cases() -> None:
    assert len(CASES) == 100
    assert {case["source_format"] for case in CASES} == {"pdf", "ofd", "png"}


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_sanitized_visual_abstractions_render_to_ocr_inputs(case: dict[str, Any]) -> None:
    visual = case["visual"]
    png = render_visual_png(visual)

    with Image.open(BytesIO(png)) as image:
        width, height = image.size

    assert png.startswith(b"\x89PNG")
    assert width > 100
    assert height > 100
    assert len(png) > 1000


def test_pdf_visual_abstractions_render_to_image_only_pdf() -> None:
    pdf_case = next(case for case in CASES if case["visual"]["kind"] == "pdf_text_layout")
    pdf = render_visual_pdf(pdf_case["visual"])

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def _parse_rule_input(rule: dict[str, Any], source_format: str) -> dict[str, Any]:
    if rule["kind"] == "pdf_text":
        text = rule["text"]
        raw = select_extractor(text)(text)
        raw.setdefault("source", {})["format"] = "pdf"
        return normalize(raw)

    if rule["kind"] == "ofd_fields":
        fields = rule.get("fields") or {}
        if fields.get("ElectronicInvoiceAirTransportReceiptNumber"):
            raw = air_itinerary.extract(fields)
            raw.setdefault("source", {})["format"] = "ofd"
            return normalize(raw)
        raise NotImplementedError("sanitized OFD invoice is not supported")

    raise NotImplementedError(f"rule input not supported: {source_format}")
