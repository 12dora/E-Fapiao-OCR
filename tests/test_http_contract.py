from __future__ import annotations

from fastapi.testclient import TestClient

import app.api.routes as routes
from app.main import create_app


def test_parse_requires_api_key_when_configured(monkeypatch):
    class LockedSettings:
        auth_enabled = True
        api_key = "expected"
        max_file_bytes = 10 * 1024 * 1024
        image_ocr_enabled = False

    monkeypatch.setattr(routes, "settings", LockedSettings())
    client = TestClient(create_app())

    resp = client.post(
        "/v1/invoices/parse",
        files={"file": ("x.pdf", b"%PDF-1.7 sanitized", "application/pdf")},
    )

    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "unauthorized"


def test_parse_rejects_too_large_file(monkeypatch):
    class SmallLimitSettings:
        auth_enabled = False
        api_key = ""
        max_file_bytes = 3
        image_ocr_enabled = False

    monkeypatch.setattr(routes, "settings", SmallLimitSettings())
    client = TestClient(create_app())

    resp = client.post(
        "/v1/invoices/parse",
        files={"file": ("x.pdf", b"%PDF-1.7 sanitized", "application/pdf")},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "invalid_input"
