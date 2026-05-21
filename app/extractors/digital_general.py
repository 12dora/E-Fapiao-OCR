"""数电普票 extractor。

输入：pdfplumber 抽出的页面文本。
输出：未归一化的 RawInvoice dict。

字段抽取逻辑下沉到 app.extractors._shared，本文件只做"按类型组装"。
"""

from __future__ import annotations

from typing import Any

from app.extractors._shared import (
    extract_invoice_code,
    extract_invoice_number,
    extract_issue_date,
    extract_issuer,
    extract_items,
    extract_parties,
    extract_price_tax,
    extract_totals,
    half_width,
)


def extract(text: str) -> dict[str, Any]:
    t = half_width(text)

    buyer, seller = extract_parties(t)
    amount_without_tax, tax_amount = extract_totals(t)
    amount_in_words, amount_with_tax = extract_price_tax(t)
    issuer = extract_issuer(t)

    return {
        "invoice_type": "digital_general",
        "invoice_number": extract_invoice_number(t),
        "invoice_code": extract_invoice_code(t),
        "issue_date": extract_issue_date(t),
        "seller": seller,
        "buyer": buyer,
        "items": extract_items(t),
        "amount_without_tax": amount_without_tax,
        "tax_amount": tax_amount,
        "amount_with_tax": amount_with_tax,
        "amount_in_words": amount_in_words,
        "remark": f"开票人:{issuer}" if issuer else None,
        "checksum": None,
        "extra": {},
        "source": {"format": "pdf", "parser_version": "0.1.0"},
    }
