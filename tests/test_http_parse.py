"""HTTP /v1/invoices/parse 端到端测试。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

SAMPLE = Path(__file__).resolve().parents[1] / "docs" / "sample" / "普票1.pdf"


def test_parse_missing_file_returns_400():
    client = TestClient(app)
    resp = client.post("/v1/invoices/parse")
    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"]["code"] == "invalid_input"


def test_parse_garbage_returns_415():
    client = TestClient(app)
    resp = client.post(
        "/v1/invoices/parse",
        files={"file": ("junk.bin", b"definitely not a pdf or image", "application/octet-stream")},
    )
    assert resp.status_code == 415
    assert resp.json()["detail"]["code"] == "unsupported_format"


def test_parse_real_pdf_returns_200():
    if not SAMPLE.is_file():
        pytest.skip("样本缺失")
    client = TestClient(app)
    resp = client.post(
        "/v1/invoices/parse",
        files={"file": ("普票1.pdf", SAMPLE.read_bytes(), "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ok"
    assert body["format"] == "pdf"
    assert body["document_type"] == "pdf-fapiao"
    assert body["invoice_type"] == "digital_general"
    assert body["data"]["document_type"] == "pdf-fapiao"
    assert body["data"]["invoice_number"] == "26317000001791661472"
    assert body["data"]["amount_with_tax"] == "211.00"
    assert body["engine"]["rule_engine"] == "attempted"
    assert body["engine"]["ocr_mode"] == "auto"
    assert body["engine"]["ocr_used"] is False
    assert body["elapsed_ms"] >= 0


def test_parse_pdf_rule_engine_unhandled_returns_machine_readable_engine_status(monkeypatch):
    from app.parsers.pdf_parser import PdfParser

    monkeypatch.setattr(PdfParser, "_extract_text", staticmethod(lambda content: ""))
    monkeypatch.setattr(PdfParser, "_extract_qr_payload", staticmethod(lambda content: None))

    client = TestClient(app)
    resp = client.post(
        "/v1/invoices/parse",
        data={"hint_type": "pdf", "ocr_mode": "disabled"},
        files={"file": ("scan.pdf", b"%PDF-1.7 fake", "application/pdf")},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "rule_unhandled"
    assert detail["engine"]["rule_engine"] == "attempted"
    assert detail["engine"]["ocr_mode"] == "disabled"
    assert detail["engine"]["ocr_required"] is True
    assert detail["engine"]["ocr_used"] is False
