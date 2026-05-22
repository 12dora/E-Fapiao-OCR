"""脱敏样本集成测试。

这些测试覆盖之前从样本校准出的关键版式分支，但所有输入都是人工合成文本或最小
OFD 容器，不依赖本地真实发票。
"""

from __future__ import annotations

import zlib

import pytest

from app.core.normalizer import normalize
from app.extractors.version_adapter import select_extractor
from app.parsers.pdf_parser import PdfParser
from app.sdk import parse_invoice
from tests.fixtures import sanitized

PDF_CASES = [
    (
        "digital_general",
        sanitized.DIGITAL_GENERAL_TEXT,
        {
            "document_type": "pdf-fapiao",
            "invoice_type": "digital_general",
            "invoice_number": "26100000000000000001",
            "issue_date": "2026-05-17",
            "buyer_name": "测试采购科技有限公司",
            "seller_name": "脱敏销售服务有限公司",
            "amount_without_tax": "199.06",
            "tax_amount": "11.94",
            "amount_with_tax": "211.00",
        },
    ),
    (
        "digital_general_tax_free",
        sanitized.DIGITAL_GENERAL_TAX_FREE_TEXT,
        {
            "document_type": "pdf-fapiao",
            "invoice_type": "digital_general",
            "invoice_number": "12345678",
            "invoice_code": "033002100111",
            "issue_date": "2024-07-03",
            "buyer_name": "脱敏买方有限公司",
            "seller_name": "脱敏免税商店",
            "amount_without_tax": "139.50",
            "tax_amount": None,
            "amount_with_tax": "139.50",
        },
    ),
    (
        "digital_general_stacked_values",
        sanitized.DIGITAL_GENERAL_STACKED_VALUES_TEXT,
        {
            "document_type": "pdf-fapiao",
            "invoice_type": "digital_general",
            "invoice_number": "26100000000000000005",
            "issue_date": "2026-05-06",
            "buyer_name": "脱敏采购科技有限公司",
            "seller_name": "脱敏销售服务有限公司",
            "amount_without_tax": "776.24",
            "tax_amount": "7.76",
            "amount_with_tax": "784.00",
        },
    ),
    (
        "digital_general_stacked_tax_free",
        sanitized.DIGITAL_GENERAL_STACKED_TAX_FREE_TEXT,
        {
            "document_type": "pdf-fapiao",
            "invoice_type": "digital_general",
            "invoice_number": "26100000000000000006",
            "issue_date": "2026-05-02",
            "buyer_name": "脱敏采购科技有限公司",
            "seller_name": "脱敏免税服务中心",
            "amount_without_tax": "300.00",
            "tax_amount": None,
            "amount_with_tax": "300.00",
        },
    ),
    (
        "digital_special_cross_line_total",
        sanitized.DIGITAL_SPECIAL_TEXT,
        {
            "document_type": "pdf-fapiao",
            "invoice_type": "digital_special",
            "invoice_number": "26100000000000000002",
            "issue_date": "2026-05-08",
            "buyer_name": "脱敏采购设备有限公司",
            "seller_name": "脱敏贸易有限公司",
            "amount_without_tax": "34.67",
            "tax_amount": "4.51",
            "amount_with_tax": "39.18",
        },
    ),
    (
        "digital_special_bare_tokens",
        sanitized.DIGITAL_SPECIAL_BARE_TEXT,
        {
            "document_type": "pdf-fapiao",
            "invoice_type": "digital_special",
            "invoice_number": "26100000000000000003",
            "issue_date": "2025-08-01",
            "buyer_name": "脱敏买方工程有限公司",
            "seller_name": "脱敏卖方酒店有限公司",
            "amount_without_tax": "267.40",
            "tax_amount": "2.67",
            "amount_with_tax": "270.07",
        },
    ),
    (
        "digital_general_toll",
        sanitized.DIGITAL_GENERAL_TOLL_TEXT,
        {
            "document_type": "pdf-fapiao",
            "invoice_type": "digital_general",
            "invoice_number": "26327902540500062081",
            "issue_date": "2026-05-05",
            "buyer_name": "脱敏采购科技有限公司",
            "seller_name": "脱敏高速公路有限公司",
            "amount_without_tax": "34.38",
            "tax_amount": "1.03",
            "amount_with_tax": "35.41",
        },
    ),
    (
        "digital_general_standalone_price_tax",
        sanitized.DIGITAL_GENERAL_STANDALONE_PRICE_TAX_TEXT,
        {
            "document_type": "pdf-fapiao",
            "invoice_type": "digital_general",
            "invoice_number": "26337000000454161517",
            "issue_date": "2026-05-06",
            "buyer_name": "脱敏采购科技有限公司",
            "seller_name": "脱敏保险服务有限公司",
            "amount_without_tax": "6839.07",
            "tax_amount": "410.34",
            "amount_with_tax": "7249.41",
        },
    ),
    (
        "rail_12306",
        sanitized.RAIL_12306_TEXT,
        {
            "document_type": "pdf-rail-12306",
            "invoice_type": "rail_12306",
            "invoice_number": "25420000000000000001",
            "issue_date": "2025-08-08",
            "buyer_name": "脱敏采购科技有限公司",
            "seller_name": "中国铁路",
            "amount_without_tax": None,
            "tax_amount": None,
            "amount_with_tax": "396.00",
        },
    ),
]


@pytest.mark.parametrize(
    "name,text,expected",
    PDF_CASES,
    ids=[case[0] for case in PDF_CASES],
)
def test_sanitized_pdf_text_cases_parse_core_fields(
    name: str,
    text: str,
    expected: dict,
) -> None:
    raw = select_extractor(text)(text)
    raw.setdefault("source", {})["format"] = "pdf"

    data = normalize(raw)
    assert data["document_type"] == expected["document_type"]
    assert data["invoice_type"] == expected["invoice_type"]
    assert data["invoice_number"] == expected["invoice_number"]
    assert data["issue_date"] == expected["issue_date"]
    assert data["buyer"]["name"] == expected["buyer_name"]
    assert data["seller"]["name"] == expected["seller_name"]
    assert data["amount_without_tax"] == expected["amount_without_tax"]
    assert data["tax_amount"] == expected["tax_amount"]
    assert data["amount_with_tax"] == expected["amount_with_tax"]
    assert data["source"]["format"] == "pdf"

    if name == "rail_12306":
        rail = data["extra"]["rail_12306"]
        assert rail["train_no"] == "G3123"
        assert rail["from_station"] == "脱敏东"
        assert rail["to_station"] == "脱敏南"
        assert rail["depart_time"] == "2025-03-21 13:53:00"
        assert rail["seat_type"] == "一等座"
        assert data["items"][0]["amount"] == "396.00"
    else:
        assert data["buyer"]["tax_id"]
        assert data["seller"]["tax_id"]
        assert data["items"]


def test_pdf_parser_pipeline_uses_sanitized_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        PdfParser,
        "_extract_text",
        staticmethod(lambda content: sanitized.DIGITAL_GENERAL_TEXT),
    )

    data = parse_invoice(b"%PDF-1.7 sanitized")
    assert data["document_type"] == "pdf-fapiao"
    assert data["invoice_type"] == "digital_general"
    assert data["invoice_number"] == "26100000000000000001"
    assert data["source"]["extracted_by"] == "text_layer"


def test_pdf_parser_uses_embedded_fields_when_text_layer_has_broken_font_map() -> None:
    content = _pdf_with_embedded_invoice_fields()
    data = parse_invoice(content, ocr_mode="disabled")

    assert data["document_type"] == "pdf-fapiao"
    assert data["invoice_type"] == "digital_general"
    assert data["invoice_number"] == "26317000000010839783"
    assert data["issue_date"] == "2026-03-09"
    assert data["amount_without_tax"] == "7963.72"
    assert data["tax_amount"] == "1035.28"
    assert data["amount_with_tax"] == "8999.00"
    assert data["buyer"]["tax_id"] == "91330600597214350R"
    assert data["seller"]["tax_id"] == "91310106MA1FYMRL1D"


def _pdf_with_embedded_invoice_fields() -> bytes:
    private = (
        b"<</Creator(gp-template)"
        b"/InvoiceNumber(26317000000010839783)"
        b"/IssueTime(\xfe\xff\x002\x000\x002\x006^t\x000\x003g\x08\x000\x009e\xe5)"
        b"/TotalAmWithoutTax(7963.72)"
        b"/TotalTaxAm(1035.28)"
        b"/TotalTax-includedAmount(8999.00)"
        b"/BuyerIdNum(91330600597214350R)"
        b"/SellerIdNum(91310106MA1FYMRL1D)>>"
    )
    compressed = zlib.compress(private)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 120] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length 4 >>\nstream\njunk\nendstream",
        b"<< /Length "
        + str(len(compressed)).encode("ascii")
        + b" /Filter /FlateDecode >>\nstream\n"
        + compressed
        + b"\nendstream",
    ]
    stream = b"BT /F1 12 Tf 30 80 Td (\x01\x02\x03\x04\x05) Tj ET"
    objects[4] = (
        f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream"
    )

    chunks = [b"%PDF-1.4\n"]
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(sum(len(chunk) for chunk in chunks))
        chunks.append(f"{i} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
    xref_offset = sum(len(chunk) for chunk in chunks)
    chunks.append(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    chunks.append(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        chunks.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    chunks.append(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return b"".join(chunks)
