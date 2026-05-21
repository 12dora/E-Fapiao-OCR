from __future__ import annotations

import json

from app import cli
from app.parsers.pdf_parser import PdfParser
from tests.fixtures import sanitized


def test_cli_parse_sanitized_pdf_stdout(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    path = tmp_path / "sanitized.pdf"
    path.write_bytes(b"%PDF-1.7 sanitized")
    monkeypatch.setattr(
        PdfParser,
        "_extract_text",
        staticmethod(lambda content: sanitized.DIGITAL_GENERAL_TEXT),
    )

    exit_code = cli.main(["parse", str(path), "--ocr-mode", "disabled"])

    assert exit_code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    assert out["data"]["invoice_number"] == "26100000000000000001"
    assert out["engine"]["ocr_mode"] == "disabled"
    assert out["engine"]["ocr_used"] is False


def test_cli_rule_unhandled_error_stderr(tmp_path, monkeypatch, capsys) -> None:
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"%PDF-1.7 sanitized")
    monkeypatch.setattr(PdfParser, "_extract_text", staticmethod(lambda content: ""))
    monkeypatch.setattr(PdfParser, "_extract_qr_payload", staticmethod(lambda content: None))

    exit_code = cli.main(["parse", str(path), "--ocr-mode", "disabled"])

    assert exit_code == 4
    err = json.loads(capsys.readouterr().err)
    assert err["code"] == "rule_unhandled"
    assert err["engine"]["ocr_required"] is True
    assert err["engine"]["ocr_mode"] == "disabled"


def test_cli_capabilities_includes_parse_modes(capsys) -> None:
    exit_code = cli.main(["capabilities"])

    assert exit_code == 0
    out = json.loads(capsys.readouterr().out)
    assert "ocr_mode" in out["parse_modes"]
    assert out["formats"]["pdf"] == "supported"
