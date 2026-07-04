"""兜底 extractor —— 优先消费二维码 payload。

数电发票二维码内容通常包含：发票号码 / 开票日期 / 金额 / 税额 / 校验码。
当文本层抽取失败时，二维码是最稳的兜底来源。
"""

from __future__ import annotations

import re
from datetime import datetime
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
    invoice_code = _pick_invoice_code(parts, invoice_number)
    issue_date = _pick_issue_date(parts, exclude={invoice_number, invoice_code})
    amounts = _pick_amounts(parts, invoice_number)

    return {
        "invoice_number": invoice_number,
        "invoice_code": invoice_code,
        "issue_date": issue_date,
        "amount_with_tax": amounts[0] if amounts else None,
        "tax_amount": amounts[1] if len(amounts) > 1 else None,
        "checksum": _pick_checksum(parts, invoice_number),
    }


def _is_valid_date8(part: str) -> bool:
    """判断一段 8 位数字是否是合理的 YYYYMMDD 日期。"""
    if not re.fullmatch(r"\d{8}", part):
        return False
    try:
        parsed = datetime.strptime(part, "%Y%m%d")
    except ValueError:
        return False
    return 1900 <= parsed.year <= 2999


def _pick_invoice_number(parts: list[str]) -> str | None:
    """按 CSV 字段顺序识别发票号码。

    税务二维码字段序大致为 发票代码 → 发票号码 → 金额 → 开票日期 → 校验码。
    发票号码是数电 20 位、历史 VAT 8 位；发票代码为 10-12 位、日期为 8 位。
    按顺序取首个「20 位」或「非日期的 8 位」纯数字，可同时避开发票代码（10-12 位）、
    开票日期（8 位日期）与靠后的校验码。
    """
    for part in parts:
        if re.fullmatch(r"\d{20}", part):
            return part
        if re.fullmatch(r"\d{8}", part) and not _is_valid_date8(part):
            return part
    # 兜底：排除日期后取最长纯数字（保持旧行为的健壮性）。
    candidates = [
        part
        for part in parts
        if re.fullmatch(r"\d{8,24}", part) and not _is_valid_date8(part)
    ]
    return max(candidates, key=len) if candidates else None


def _pick_invoice_code(parts: list[str], invoice_number: str | None) -> str | None:
    for part in parts:
        if part != invoice_number and re.fullmatch(r"\d{10,12}", part):
            return part
    return None


def _pick_issue_date(parts: list[str], exclude: set[str | None] | None = None) -> str | None:
    exclude = exclude or set()
    for part in parts:
        if part in exclude:
            continue
        if _is_valid_date8(part):
            return f"{part[:4]}-{part[4:6]}-{part[6:8]}"
        m = re.fullmatch(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?", part)
        if m:
            y, mo, d = m.groups()
            try:
                datetime(int(y), int(mo), int(d))
            except ValueError:
                continue
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
