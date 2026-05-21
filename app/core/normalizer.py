"""Normalizer —— 字段归一化。

职责：
  - 金额：所有金额字段统一为字符串两位小数，如 "100.00"
  - 日期：统一 YYYY-MM-DD（数字校验，避免 "0000-00-00"）
  - 字段填充：DESIGN.md §6 列出的字段，缺则补 None，不省略键
  - 字符串：去前后空白
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from app import __version__

_AMOUNT_KEYS = {"amount_without_tax", "tax_amount", "amount_with_tax"}
_ITEM_AMOUNT_KEYS = {"unit_price", "amount", "tax_amount", "quantity"}


def normalize(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "document_type": _str_or_none(raw.get("document_type")) or _infer_document_type(raw),
        "invoice_type": raw.get("invoice_type"),
        "invoice_number": _str_or_none(raw.get("invoice_number")),
        "invoice_code": _str_or_none(raw.get("invoice_code")),
        "issue_date": _normalize_date(raw.get("issue_date")),
        "seller": _normalize_party(raw.get("seller")),
        "buyer": _normalize_party(raw.get("buyer")),
        "items": [_normalize_item(it) for it in (raw.get("items") or [])],
        "amount_without_tax": _money(raw.get("amount_without_tax")),
        "tax_amount": _money(raw.get("tax_amount")),
        "amount_with_tax": _money(raw.get("amount_with_tax")),
        "amount_in_words": _str_or_none(raw.get("amount_in_words")),
        "remark": _str_or_none(raw.get("remark")),
        "checksum": _str_or_none(raw.get("checksum")),
        "extra": raw.get("extra") or {},
        "source": _normalize_source(raw.get("source")),
    }
    return out


def _normalize_party(p: dict[str, Any] | None) -> dict[str, Any]:
    p = p or {}
    return {
        "name": _str_or_none(p.get("name")),
        "tax_id": _str_or_none(p.get("tax_id")),
        "address": _str_or_none(p.get("address")),
        "bank": _str_or_none(p.get("bank")),
    }


def _normalize_item(it: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": _str_or_none(it.get("name")),
        "spec": _str_or_none(it.get("spec")),
        "unit": _str_or_none(it.get("unit")),
        "quantity": _money(it.get("quantity")) if it.get("quantity") else None,
        "unit_price": _money(it.get("unit_price")),
        "amount": _money(it.get("amount")),
        "tax_rate": _str_or_none(it.get("tax_rate")),
        "tax_amount": _money(it.get("tax_amount")),
    }


def _normalize_source(s: dict[str, Any] | None) -> dict[str, Any]:
    s = s or {}
    return {
        "format": s.get("format") or "pdf",
        "parser_version": s.get("parser_version") or __version__,
        "extracted_by": s.get("extracted_by") or "text_layer",
        "ocr_vendor": _str_or_none(s.get("ocr_vendor")),
    }


def _infer_document_type(raw: dict[str, Any]) -> str:
    fmt = (raw.get("source") or {}).get("format")
    invoice_type = raw.get("invoice_type")
    if fmt == "ofd" and invoice_type == "air_itinerary":
        return "ofd-air-itinerary"
    if fmt == "ofd":
        return "ofd-fapiao"
    if fmt == "pdf" and invoice_type == "rail_12306":
        return "pdf-rail-12306"
    if fmt == "image" and invoice_type == "air_itinerary":
        return "image-air-itinerary"
    if fmt == "image":
        return "image-fapiao"
    return "pdf-fapiao"


def _str_or_none(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _money(v: Any) -> str | None:
    if v is None or v == "" or v == "*":
        return None
    try:
        cleaned = str(v).replace(",", "").replace("¥", "").replace("￥", "").strip()
        return str(Decimal(cleaned).quantize(Decimal("0.01")))
    except (InvalidOperation, ValueError):
        return None


def _normalize_date(v: Any) -> str | None:
    s = _str_or_none(v)
    if not s:
        return None
    # 已经是 YYYY-MM-DD
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            int(s[:4])
            int(s[5:7])
            int(s[8:10])
            return s
        except ValueError:
            return None
    return None
