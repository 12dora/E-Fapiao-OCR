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
    assert body["invoice_type"] == "digital_general"
    assert body["data"]["invoice_number"] == "26317000001791661472"
    assert body["data"]["amount_with_tax"] == "211.00"
    assert body["elapsed_ms"] >= 0
