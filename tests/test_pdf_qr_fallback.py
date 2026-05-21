from app.errors import RuleEngineUnhandled
from app.parsers.pdf_parser import PdfParser


def test_pdf_parser_uses_qr_when_text_layer_is_empty(monkeypatch):
    payload = (
        "01,10,033002100111,26317000001791661472,"
        "211.00,20260517,12345678901234567890"
    )
    monkeypatch.setattr(PdfParser, "_extract_text", staticmethod(lambda content: ""))
    monkeypatch.setattr(
        PdfParser,
        "_extract_qr_payload",
        staticmethod(lambda content: payload),
    )

    raw = PdfParser().parse(b"fake pdf bytes")
    assert raw["invoice_type"] == "digital_general"
    assert raw["invoice_number"] == "26317000001791661472"
    assert raw["issue_date"] == "2026-05-17"
    assert raw["amount_with_tax"] == "211.00"
    assert raw["source"]["extracted_by"] == "qrcode"


def test_pdf_parser_reports_rule_engine_unhandled_when_text_and_qr_missing(monkeypatch):
    monkeypatch.setattr(PdfParser, "_extract_text", staticmethod(lambda content: ""))
    monkeypatch.setattr(PdfParser, "_extract_qr_payload", staticmethod(lambda content: None))

    try:
        PdfParser().parse(b"fake pdf bytes", ocr_mode="disabled")
    except RuleEngineUnhandled as e:
        assert e.file_format == "pdf"
        assert e.ocr_required is True
        assert "规则引擎无法解析" in str(e)
    else:
        raise AssertionError("PDF 文本层与二维码都缺失时应返回规则引擎未覆盖语义")
