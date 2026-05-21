"""数电增值税专用发票 extractor。

与普票 80% 同构，差异点：
  - invoice_type = "digital_special"
  - 部分版式（如"全国统一红章"版）发票号 / 日期 / 双方信息位置异于普通版
    → 用 helpers 主路径解析失败时启用 "bare-token 兜底"：
        · 单独成行的 20 位纯数字 → invoice_number
        · 单独成行的 "YYYY年MM月DD日" → issue_date
        · 单独成行的 "<公司名> <公司名>" 两段 → buyer/seller name
        · 单独成行的 "<税号> <税号>" 两段 → buyer/seller tax_id
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

    invoice_number = extract_invoice_number(t)
    issue_date = extract_issue_date(t)
    buyer, seller = extract_parties(t)
    amount_without_tax, tax_amount = extract_totals(t)
    amount_in_words, amount_with_tax = extract_price_tax(t)
    issuer = extract_issuer(t)

    return {
        "invoice_type": "digital_special",
        "invoice_number": invoice_number,
        "invoice_code": extract_invoice_code(t),
        "issue_date": issue_date,
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
