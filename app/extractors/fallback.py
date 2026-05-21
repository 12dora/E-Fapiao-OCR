"""兜底 extractor —— 优先消费二维码 payload。

数电发票二维码内容通常包含：发票号码 / 开票日期 / 金额 / 税额 / 校验码。
当文本层抽取失败时，二维码是最稳的兜底来源。
"""

from __future__ import annotations

import re
from typing import Any

from app.errors import ParseFailed


def extract(qr_payload: str | None, text: str | None = None) -> dict[str, Any]:
    if not qr_payload:
        raise ParseFailed("无法识别发票版式，且未找到二维码兜底数据")

    fields = _parse_qr_payload(qr_payload)
    if not fields.get("invoice_number"):
        raise ParseFailed("二维码内容缺少发票号码")

    return {
        "invoice_type": "digital_general",
        "invoice_number": fields.get("invoice_number"),
        "invoice_code": fields.get("invoice_code"),
        "issue_date": fields.get("issue_date"),
        "seller": {},
        "buyer": {},
        "items": [],
        "amount_without_tax": None,
        "tax_amount": fields.get("tax_amount"),
        "amount_with_tax": fields.get("amount_with_tax"),
        "amount_in_words": None,
        "remark": None,
        "checksum": fields.get("checksum"),
        "extra": {},
        "source": {"format": "pdf", "parser_version": "0.1.0"},
    }


def _parse_qr_payload(payload: str) -> dict[str, str | None]:
    """解析常见税务二维码 payload。

    常见格式为逗号分隔字段，历史 VAT 码大致包含：
    版本/类型、发票代码、发票号码、金额、开票日期、校验码。
    数电票可能没有发票代码，因此这里用启发式挑选关键字段。
    """
    parts = [part.strip() for part in re.split(r"[,，\n\r\t|]", payload) if part.strip()]
    invoice_number = _pick_invoice_number(parts)
    issue_date = _pick_issue_date(parts)
    amounts = _pick_amounts(parts, invoice_number)

    return {
        "invoice_number": invoice_number,
        "invoice_code": _pick_invoice_code(parts, invoice_number),
        "issue_date": issue_date,
        "amount_with_tax": amounts[0] if amounts else None,
        "tax_amount": amounts[1] if len(amounts) > 1 else None,
        "checksum": _pick_checksum(parts, invoice_number),
    }


def _pick_invoice_number(parts: list[str]) -> str | None:
    candidates = [part for part in parts if re.fullmatch(r"\d{8,24}", part)]
    if not candidates:
        return None
    return max(candidates, key=len)


def _pick_invoice_code(parts: list[str], invoice_number: str | None) -> str | None:
    for part in parts:
        if part != invoice_number and re.fullmatch(r"\d{10,12}", part):
            return part
    return None


def _pick_issue_date(parts: list[str]) -> str | None:
    for part in parts:
        m = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", part)
        if m:
            y, mo, d = m.groups()
            return f"{y}-{mo}-{d}"
        m = re.fullmatch(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?", part)
        if m:
            y, mo, d = m.groups()
            return f"{y}-{int(mo):02d}-{int(d):02d}"
    return None


def _normalize_amount(value: str) -> str | None:
    if not re.fullmatch(r"[¥￥]?-?\d+\.\d{1,2}", value):
        return None
    return value.lstrip("¥￥")


def _pick_amounts(parts: list[str], invoice_number: str | None) -> list[str]:
    amounts: list[str] = []
    for part in parts:
        if part == invoice_number:
            continue
        amount = _normalize_amount(part)
        if amount is not None:
            amounts.append(amount)
    return amounts


def _pick_checksum(parts: list[str], invoice_number: str | None) -> str | None:
    for part in reversed(parts):
        if part != invoice_number and re.fullmatch(r"[0-9A-Za-z]{15,32}", part):
            return part
    return None
