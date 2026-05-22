"""数电普票 / 专票 共享的字段抽取 helpers。

仅做"字符串切片"，不做归一化（归一化是 Normalizer 的活儿）。
"""

from __future__ import annotations

import re
from typing import Any

# 同时容忍 ¥ ￥ ´（某些 PDF 字体把 ¥ 渲染为 ´）
_YUAN = r"[¥￥´]"
COMPANY_TAIL = r"(?:公司|酒店|医院|学校|集团|分公司|事务所|工厂|厂|店|社|中心|餐厅|饭店|个体工商户)"

INVOICE_NO = re.compile(r"发\s*票\s*号码[:：\s]*([0-9A-Za-z]{8,24})")
INVOICE_CODE = re.compile(r"发\s*票\s*代码[:：\s]*([0-9A-Za-z]{10,12})")
ISSUE_DATE = re.compile(
    r"开\s*票\s*日期[:：\s]*([0-9]\s*[0-9]\s*[0-9]\s*[0-9])\s*年\s*"
    r"([0-9]\s*[0-9]?)\s*月\s*([0-9]\s*[0-9]?)\s*日"
)
NAME = re.compile(
    # - 首字必须为汉字/字母/数字（防止把残留冒号、星号当成名字）
    # - 整体不得包含另一个 "名称" 标签（防止跨字段误命中）
    # - "名称" 与冒号之间的分隔符限制为 \t 与空格（不含 \n），
    #   否则会跨行抓到下一行首字符（专票3 的 "买 名称: 售 名称:\n方 方"）
    r"名[ \t]*称[ \t:]*"
    r"([一-龥A-Za-z0-9](?:(?!名[ \t]*称).)*?)"
    r"(?=[ \t]+(?:销|售|方|信|统一|纳税)|$)",
    re.MULTILINE,
)
NAME_PAIR_INLINE = re.compile(
    r"名[ \t]*称[ \t:]*"
    r"([^\n]+?)"
    r"[ \t]+名[ \t]*称[ \t:]*"
    r"([^\n]+?)"
    r"(?=[ \t]+(?:买|售|方|信|统一|纳税)|$)",
    re.MULTILINE,
)
TAX_ID = re.compile(
    r"(?:统\s*一\s*社\s*会\s*信\s*用\s*代\s*码|纳\s*税\s*人\s*识\s*别\s*号)"
    r"[/\s]*(?:纳\s*税\s*人\s*识\s*别\s*号)?[:：\s]*([A-Z0-9]{15,20})"
)
# "合 计 ¥199.06 ¥11.94"  或  "合 计 ¥199.06 *"
TOTAL_LINE_INLINE = re.compile(
    rf"合\s*计\s*{_YUAN}\s*([0-9.\-]+)\s+(?:{_YUAN}\s*([0-9.\-]+)|[*＊]+)"
)
# 专票2 这种 "合 计\n¥984.08 ¥127.92"（标签与金额跨行）
TOTAL_PAIR_LINE = re.compile(
    rf"^{_YUAN}\s*([0-9.\-]+)\s+(?:{_YUAN}\s*([0-9.\-]+)|[*＊]+)\s*$",
    re.MULTILINE,
)
LEGACY_AMOUNT_PAIR_LINE = re.compile(
    rf"^{_YUAN}\s*(-?[0-9.]+)\s+{_YUAN}\s*(-?[0-9.]+)\s*$",
    re.MULTILINE,
)
LEGACY_PRICE_TAX_LINE = re.compile(
    rf"^([一-龥零壹贰叁肆伍陆柒捌玖拾佰仟万亿圆元角分整]+)\s+"
    rf"{_YUAN}\s*(-?[0-9.]+)\s*$"
)
PRICE_TAX = re.compile(
    rf"价\s*税\s*合\s*计.*?大\s*写[)\s]*(.+?)\s*\(?\s*小\s*写\s*\)?\s*{_YUAN}?\s*(-?[0-9.]+)"
)
ISSUER = re.compile(r"开\s*票\s*人[:：\s]*(\S+)")

ITEM_TAIL = re.compile(r"(-?\d+\.\d{2})\s+(\d{1,2}%|\*)\s+(-?\d+\.\d{2}|\*)\s*$")
ITEM_TAIL_TAX_FREE = re.compile(r"(-?\d+\.\d{2})\s+(不征税|免税|零税率)(?:\s+[*＊]+)?\s*$")
LEGACY_ITEM_TAIL = re.compile(
    r"(-?\d+\.\d{2})\s+(-?\d+\.\d{2})\s+(\d{1,2}%|不征税|免税|零税率|\*)\s+"
    r"(-?\d+\.\d{2}|[*＊]+)\s*$"
)
GENERAL_ETICKET_ITEM_TAIL = re.compile(
    r"\s+\d+(?:\.\d+)?\s+(-?\d+\.\d{2})\s+(-?\d+\.\d{2})\s+(-?\d+\.\d{2})\s+"
    r"(-?\d+\.\d{2})\s*$"
)
BARE_INV_NO = re.compile(r"(?<!\d)(\d{20})(?!\d)")
BARE_DATE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")
BARE_TAX_PAIR = re.compile(r"^\s*([A-Z0-9]{15,20})\s+([A-Z0-9]{15,20})\s*$", re.MULTILINE)
BARE_TAX_ID = re.compile(r"^[A-Z0-9]{15,20}$")
# 整行两个主体名称（用空白分隔），用于红章/水印版式标签抽不出时兜底。
BARE_NAME_PAIR = re.compile(
    rf"^\s*([一-龥A-Za-z0-9()（）]{{4,}}{COMPANY_TAIL})\s+"
    rf"([一-龥A-Za-z0-9()（）]{{4,}}{COMPANY_TAIL})\s*$",
    re.MULTILINE,
)
BARE_COMPANY_NAME = re.compile(rf"([一-龥A-Za-z0-9()（）]{{4,}}{COMPANY_TAIL})")
FLAT_PRICE_TAX_LINE = re.compile(
    rf"([零壹贰叁肆伍陆柒捌玖拾佰仟万亿圆元角分整]+)\s+.*?{_YUAN}\s*(-?[0-9.]+)"
)
TOLL_TOTAL = re.compile(
    r"(?<!\d)(-?\d+\.\d{2})\s+(?:\d{1,2}%|不征税|免税|零税率)\s+(-?\d+\.\d{2}|[*＊]+)(?!\d)"
)
TOLL_ITEM = re.compile(
    r"(?P<name>\*[^\s]*通行费)\s+"
    r"(?P<plate>[^\s]+)\s+"
    r"(?P<vehicle>[^\s]+)\s+"
    r"(?P<date>\d{8})\s+"
    r"(?P<amount>-?\d+\.\d{2})\s+"
    r"(?P<rate>\d{1,2}%|不征税|免税|零税率)\s+"
    r"(?P<tax>-?\d+\.\d{2}|[*＊]+)"
)
TAIL_LAYOUT_PARTIES = re.compile(
    rf"(?<!\d)(?:23|24|25|26)\d{{18}}(?!\d)\s+"
    r"20\d{2}年\d{1,2}月\d{1,2}日\s+"
    r"(?P<buyer_tax>[A-Z0-9]{15,20})\s+"
    rf"(?P<seller_name>[一-龥A-Za-z0-9()（）]{{4,}}{COMPANY_TAIL})\s*"
    r"(?P<seller_tax>[A-Z0-9]{15,20})"
)


def half_width(s: str) -> str:
    """全角 → 半角（仅针对会影响正则的字符）。"""
    return (
        s.replace("：", ":")
        .replace("（", "(")
        .replace("）", ")")
        .replace("￥", "¥")
        .replace("＊", "*")
        .replace("⼦", "子")
        .replace("⼈", "人")
        .replace("⽅", "方")
        .replace("⾦", "金")
        .replace("⼤", "大")
    )


def first(pat: re.Pattern[str], text: str) -> str | None:
    m = pat.search(text)
    return m.group(1).strip() if m else None


def extract_invoice_number(text: str) -> str | None:
    invoice_number = first(INVOICE_NO, text)
    if invoice_number:
        return invoice_number
    label_value = _legacy_invoice_no_from_lines(text)
    if label_value:
        return label_value
    m = re.search(r"(?<!\d)((?:23|24|25|26)\d{18})(?!\d)", text)
    if m:
        return m.group(1)
    return None


def extract_invoice_code(text: str) -> str | None:
    invoice_code = first(INVOICE_CODE, text)
    if invoice_code:
        return invoice_code
    m = re.search(r"增值税电子普通发票\s+([0-9A-Za-z]{10,12})", text)
    if m:
        return m.group(1)
    lines = [line.strip() for line in text.splitlines()]
    for i, line in enumerate(lines):
        if re.fullmatch(r"发\s*票\s*代码[:：]?", line):
            for candidate in lines[i + 1 : i + 20]:
                m = re.fullmatch(r"([0-9A-Za-z]{10,12})", candidate)
                if m:
                    return m.group(1)
    return None


def _legacy_invoice_no_from_lines(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines()]
    for i, line in enumerate(lines):
        if re.fullmatch(r"发\s*票\s*号码[:：]?", line):
            for candidate in lines[i + 1 : i + 15]:
                if re.search(r"机器编号|校\s*验\s*码|开户行|账号", candidate):
                    continue
                m20 = re.search(r"(?<!\d)((?:23|24|25|26)\d{18})(?!\d)", candidate)
                if m20:
                    return m20.group(1)
                matches = re.findall(r"(?<!\d)(\d{8})(?!\d)", candidate)
                if matches:
                    return matches[0]
    return None


def extract_issue_date(text: str) -> str | None:
    m = ISSUE_DATE.search(text)
    if not m:
        m = BARE_DATE.search(text)
    if not m:
        m = re.search(r"(?<!\d)(20\d{2})\s+(\d{1,2})\s+(\d{1,2})(?!\d)", text)
    if not m:
        return None
    y, mo, d = m.groups()
    y = re.sub(r"\s+", "", y)
    mo = re.sub(r"\s+", "", mo)
    d = re.sub(r"\s+", "", d)
    return f"{y}-{int(mo):02d}-{int(d):02d}"


def extract_parties(text: str) -> tuple[dict, dict]:
    """返回 (buyer, seller) 两个 dict，缺值为 None。"""
    names = _extract_party_names(text)
    names = [name for name in names if name]
    tax_ids = TAX_ID.findall(text)

    def party(idx: int) -> dict[str, Any]:
        return {
            "name": names[idx].strip() if len(names) > idx else None,
            "tax_id": tax_ids[idx] if len(tax_ids) > idx else None,
            "address": None,
            "bank": None,
        }

    buyer, seller = party(0), party(1)
    apply_tail_layout_party_fallback(text, buyer, seller)
    apply_bare_party_fallback(text, buyer, seller)
    return buyer, seller


def _extract_party_names(text: str) -> list[str]:
    pair = NAME_PAIR_INLINE.search(text)
    if pair:
        return [
            name
            for name in (_clean_party_name(pair.group(1)), _clean_party_name(pair.group(2)))
            if name
        ]
    return [name for raw_name in NAME.findall(text) if (name := _clean_party_name(raw_name))]


def _clean_party_name(name: str) -> str | None:
    name = name.strip()
    name = re.sub(r"\s+(?:购|买|销|售|方|信|息)$", "", name).strip()
    name = name.strip(":：")
    compact_name = re.sub(r"(?<=[一-龥])\s+(?=[一-龥])", "", name)
    company = BARE_COMPANY_NAME.search(compact_name)
    if company:
        name = company.group(1)
    if not name:
        return None
    if len(name) <= 1:
        return None
    if "项目名称" in name or "规格型号" in name:
        return None
    if "车牌号" in name or "税率" in name:
        return None
    return name


def extract_totals(text: str) -> tuple[str | None, str | None]:
    """合计行 → (amount_without_tax, tax_amount)。优先同行匹配，回退到跨行。"""
    m = TOTAL_LINE_INLINE.search(text)
    if m:
        return m.group(1), m.group(2)

    # 跨行：先确认存在 "合 计" 标签，再在其后找一行 ¥xxx ¥yyy
    label = re.search(r"合\s*计", text)
    if label:
        tail = text[label.end():]
        m2 = TOTAL_PAIR_LINE.search(tail)
        if m2:
            return m2.group(1), m2.group(2)

    if "通行费" in text:
        m3 = TOLL_TOTAL.search(text)
        if m3:
            tax_amount = None if m3.group(2).startswith("*") else m3.group(2)
            return m3.group(1), tax_amount
    return None, None


def extract_price_tax(text: str) -> tuple[str | None, str | None]:
    """价税合计 → (amount_in_words, amount_with_tax)。"""
    m = PRICE_TAX.search(text)
    if not m:
        for line in text.splitlines():
            m2 = LEGACY_PRICE_TAX_LINE.match(line.strip())
            if m2:
                if re.search(r"[零壹贰叁肆伍陆柒捌玖拾佰仟万亿圆元角分整]", m2.group(1)):
                    return m2.group(1), m2.group(2)
            m3 = FLAT_PRICE_TAX_LINE.search(line.strip())
            if m3:
                return m3.group(1), m3.group(2)
        standalone = _standalone_price_tax_amount(text)
        if standalone:
            return None, standalone
        return None, None
    amount_in_words = re.sub(r"\s+", "", m.group(1))
    if not re.search(r"[零壹贰叁肆伍陆柒捌玖拾佰仟万亿圆元角分整]", amount_in_words):
        for line in text.splitlines():
            m2 = LEGACY_PRICE_TAX_LINE.match(line.strip())
            if m2 and re.search(
                r"[零壹贰叁肆伍陆柒捌玖拾佰仟万亿圆元角分整]",
                m2.group(1),
            ):
                return m2.group(1), m2.group(2)
            m3 = FLAT_PRICE_TAX_LINE.search(line.strip())
            if m3:
                return m3.group(1), m3.group(2)
        standalone = _standalone_price_tax_amount(text)
        if standalone:
            return None, standalone
        return None, None
    return amount_in_words, m.group(2)


def extract_issuer(text: str) -> str | None:
    return first(ISSUER, text)


def extract_items(text: str) -> list[dict[str, Any]]:
    """从 "项目名称 ..." 表头之后到 "合计" 之前提取行项目。

    一期 best-effort：
      - 名称可能跨行（专票多行品名），用 "尾部金额三元组" 在行尾的命中作为切分锚点
      - 名称不命中的连续行作为上一项的续行追加到 name
    """
    lines = text.splitlines()
    header_idx = end_idx = None
    for i, line in enumerate(lines):
        compact_line = "".join(line.split())
        if "项目名称" in compact_line and "金额" in compact_line:
            header_idx = i
        elif header_idx is not None and re.match(r"\s*合\s*计", line):
            end_idx = i
            break
    if header_idx is None or end_idx is None:
        return _extract_legacy_items(lines)

    items: list[dict[str, Any]] = []
    pending_name_parts: list[str] = []
    for line in lines[header_idx + 1 : end_idx]:
        line = line.strip()
        if not line:
            continue
        m = ITEM_TAIL.search(line)
        if m:
            prefix = line[: m.start()].strip()
            name = " ".join([*pending_name_parts, prefix]).strip() or None
            pending_name_parts = []
            items.append(
                {
                    "name": name,
                    "spec": None,
                    "unit": None,
                    "quantity": None,
                    "unit_price": None,
                    "amount": m.group(1),
                    "tax_rate": None if m.group(2) == "*" else m.group(2),
                    "tax_amount": None if m.group(3) == "*" else m.group(3),
                }
            )
            continue

        m2 = ITEM_TAIL_TAX_FREE.search(line)
        if m2:
            prefix = line[: m2.start()].strip()
            name = " ".join([*pending_name_parts, prefix]).strip() or None
            pending_name_parts = []
            items.append(
                {
                    "name": name,
                    "spec": None,
                    "unit": None,
                    "quantity": None,
                    "unit_price": None,
                    "amount": m2.group(1),
                    "tax_rate": m2.group(2),
                    "tax_amount": "0.00",
                }
            )
        else:
            pending_name_parts.append(line)
    if items:
        return items
    tail_items = _extract_tail_items(lines)
    return tail_items or _extract_toll_items(lines)


def _extract_legacy_items(lines: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for idx, line in enumerate(lines):
        m = LEGACY_ITEM_TAIL.search(line.strip())
        tax_rate = None
        if not m:
            m = GENERAL_ETICKET_ITEM_TAIL.search(line.strip())
            if not m:
                continue
            prefix = line[: m.start()].strip()
            amount = m.group(4)
            tax_amount = m.group(3)
            unit_price = m.group(1)
            try:
                tax_rate = f"{float(tax_amount) / float(amount):.2f}"
            except (ValueError, ZeroDivisionError):
                tax_rate = None
        else:
            prefix = line[: m.start()].strip()
            unit_price = m.group(1)
            amount = m.group(2)
            tax_rate = None if m.group(3) == "*" else m.group(3)
            tax_amount = None if m.group(4).startswith("*") else m.group(4)
        suffix_parts: list[str] = []
        for continuation in lines[idx + 1 : idx + 3]:
            if continuation.startswith(_YUAN.strip("[]")) or re.search(
                r"合\s*计|价\s*税", continuation
            ):
                break
            if re.fullmatch(r"[一-龥A-Za-z0-9（）()]+", continuation.strip()):
                suffix_parts.append(continuation.strip())
        name = "".join([prefix, *suffix_parts]).strip() or None
        items.append(
            {
                "name": name,
                "spec": None,
                "unit": None,
                "quantity": None,
                "unit_price": unit_price,
                "amount": amount,
                "tax_rate": tax_rate,
                "tax_amount": tax_amount,
            }
        )
    return items


def _extract_tail_items(lines: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or any(
            marker in stripped
            for marker in (
                "合计",
                "价税",
                "开票人",
                "购",
                "买",
                "方",
                "销",
                "售",
            )
        ):
            continue
        m = ITEM_TAIL.search(stripped)
        if m:
            items.append(
                {
                    "name": stripped[: m.start()].strip() or None,
                    "spec": None,
                    "unit": None,
                    "quantity": None,
                    "unit_price": None,
                    "amount": m.group(1),
                    "tax_rate": None if m.group(2) == "*" else m.group(2),
                    "tax_amount": None if m.group(3) == "*" else m.group(3),
                }
            )
            continue
        m = ITEM_TAIL_TAX_FREE.search(stripped)
        if m:
            items.append(
                {
                    "name": stripped[: m.start()].strip() or None,
                    "spec": None,
                    "unit": None,
                    "quantity": None,
                    "unit_price": None,
                    "amount": m.group(1),
                    "tax_rate": m.group(2),
                    "tax_amount": "0.00",
                }
            )
            continue
        m = LEGACY_ITEM_TAIL.search(stripped)
        if m:
            items.append(
                {
                    "name": stripped[: m.start()].strip() or None,
                    "spec": None,
                    "unit": None,
                    "quantity": None,
                    "unit_price": m.group(1),
                    "amount": m.group(2),
                    "tax_rate": None if m.group(3) == "*" else m.group(3),
                    "tax_amount": None if m.group(4).startswith("*") else m.group(4),
                }
            )
            continue
        m = GENERAL_ETICKET_ITEM_TAIL.search(stripped)
        if m:
            items.append(
                {
                    "name": stripped[: m.start()].strip() or None,
                    "spec": None,
                    "unit": None,
                    "quantity": None,
                    "unit_price": m.group(1),
                    "amount": m.group(4),
                    "tax_rate": None,
                    "tax_amount": m.group(3),
                }
            )
    return items


def _extract_toll_items(lines: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for idx, line in enumerate(lines):
        candidate = line.strip()
        if idx + 1 < len(lines):
            candidate = f"{candidate} {lines[idx + 1].strip()}"
        m = TOLL_ITEM.search(candidate)
        if not m:
            continue
        tax_amount = m.group("tax")
        items.append(
            {
                "name": m.group("name"),
                "spec": None,
                "unit": None,
                "quantity": None,
                "unit_price": None,
                "amount": m.group("amount"),
                "tax_rate": m.group("rate"),
                "tax_amount": None if tax_amount.startswith("*") else tax_amount,
            }
        )
    return items


def _standalone_price_tax_amount(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines()]
    seen_price_tax = False
    for line in lines:
        compact = "".join(line.split())
        if "价税合计" in compact:
            seen_price_tax = True
            continue
        if not seen_price_tax:
            continue
        if re.fullmatch(rf"{_YUAN}\s*(-?[0-9.]+)", line):
            return re.sub(rf"^{_YUAN}\s*", "", line)
    return None


def apply_bare_party_fallback(text: str, buyer: dict[str, Any], seller: dict[str, Any]) -> None:
    if _needs_party_name_fallback(buyer.get("name")) or _needs_party_name_fallback(
        seller.get("name")
    ):
        m = BARE_NAME_PAIR.search(text)
        if m:
            if _needs_party_name_fallback(buyer.get("name")):
                buyer["name"] = m.group(1).strip()
            if _needs_party_name_fallback(seller.get("name")):
                seller["name"] = m.group(2).strip()

    if not buyer.get("tax_id") or not seller.get("tax_id"):
        m = BARE_TAX_PAIR.search(text)
        if m:
            buyer["tax_id"] = buyer.get("tax_id") or m.group(1)
            seller["tax_id"] = seller.get("tax_id") or m.group(2)

    if _needs_party_name_fallback(buyer.get("name")) or _needs_party_name_fallback(
        seller.get("name")
    ):
        companies = _bare_company_names(text)
        if len(companies) >= 2:
            if _needs_party_name_fallback(buyer.get("name")):
                buyer["name"] = companies[0]
            if _needs_party_name_fallback(seller.get("name")):
                seller["name"] = companies[1]


def apply_tail_layout_party_fallback(
    text: str,
    buyer: dict[str, Any],
    seller: dict[str, Any],
) -> None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for idx, line in enumerate(lines):
        if not re.fullmatch(r"(?:23|24|25|26)\d{18}", line):
            continue
        if idx + 5 >= len(lines) or not BARE_DATE.search(lines[idx + 1]):
            continue
        buyer_name, buyer_tax, seller_name, seller_tax = lines[idx + 2 : idx + 6]
        if not BARE_TAX_ID.fullmatch(buyer_tax) or not BARE_TAX_ID.fullmatch(seller_tax):
            continue
        buyer["name"] = buyer_name
        buyer["tax_id"] = buyer_tax
        seller["name"] = seller_name
        seller["tax_id"] = seller_tax
        return

    m = TAIL_LAYOUT_PARTIES.search(text)
    if not m:
        return
    buyer["tax_id"] = buyer.get("tax_id") or m.group("buyer_tax")
    seller["name"] = m.group("seller_name")
    seller["tax_id"] = m.group("seller_tax")
    buyer_name = _tail_layout_buyer_name(lines)
    if buyer_name:
        buyer["name"] = buyer_name


def _tail_layout_buyer_name(lines: list[str]) -> str | None:
    for line in lines:
        if not re.search(r"\b20\d{6}\b", line):
            continue
        tail = re.split(r"\b20\d{6}\b", line, maxsplit=1)[-1]
        matches = list(BARE_COMPANY_NAME.finditer(tail))
        if matches:
            return matches[-1].group(1).strip()
    return None


def _bare_company_names(text: str) -> list[str]:
    names: list[str] = []
    for m in BARE_COMPANY_NAME.finditer(text):
        name = m.group(1).strip()
        if name in names:
            continue
        if any(skip in name for skip in ("国家税务总局", "项目名称")):
            continue
        names.append(name)
    return names


def _needs_party_name_fallback(name: Any) -> bool:
    if not name:
        return True
    if len(str(name).strip()) <= 1:
        return True
    return "项目名称" in str(name) or "规格型号" in str(name)
