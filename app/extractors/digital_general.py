"""数电普票 extractor。

输入：pdfplumber 抽出的页面文本。
输出：未归一化的 RawInvoice dict（由 Normalizer 后处理）。

设计要点：
  - 半角/全角冒号、括号统一为半角后再正则
  - "购方/销方" 在同一行（pdfplumber 把垂直字符 "购买方" 拆开），
    用 "名称" / "统一社会信用代码" 在一行内出现两次的特征区分
  - "*" 表示该列缺失（普票2 的税额场景），归一化为 None
  - 行项目放进 items 列表，按"项目名称 ... 税率 税额"分列解析
"""

from __future__ import annotations

import re
from typing import Any

INVOICE_NO = re.compile(r"发票号码[:\s]*([0-9A-Za-z]+)")
ISSUE_DATE = re.compile(r"开票日期[:\s]*(\d{4})年(\d{1,2})月(\d{1,2})日")
NAME = re.compile(
    r"名\s*称[:\s]*([^\s][^\n]*?)(?=\s+(?:销|售|方|信|统一|纳税|$)|$)",
    re.MULTILINE,
)
TAX_ID = re.compile(r"(?:统一社会信用代码|纳税人识别号)[/\s]*(?:纳税人识别号)?[:\s]*([A-Z0-9]{15,20})")
TOTAL_LINE = re.compile(r"合\s*计\s*[¥￥´]\s*([0-9.\-]+)\s+(?:[¥￥´]\s*([0-9.\-]+)|\*)")
PRICE_TAX = re.compile(r"价税合计.*?大写[)\s]*(\S+?)\s*\(?小写\)?\s*[¥￥´]?\s*([0-9.]+)")
ISSUER = re.compile(r"开票人[:\s]*(\S+)")


def _half_width(s: str) -> str:
    return (
        s.replace("：", ":")
        .replace("（", "(")
        .replace("）", ")")
        .replace("￥", "¥")
    )


def extract(text: str) -> dict[str, Any]:
    t = _half_width(text)

    invoice_number = _first(INVOICE_NO, t)
    issue_date_match = ISSUE_DATE.search(t)
    if issue_date_match:
        y, m, d = issue_date_match.groups()
        issue_date = f"{y}-{int(m):02d}-{int(d):02d}"
    else:
        issue_date = None

    names = NAME.findall(t)
    buyer_name = names[0].strip() if len(names) >= 1 else None
    seller_name = names[1].strip() if len(names) >= 2 else None

    tax_ids = TAX_ID.findall(t)
    buyer_tax_id = tax_ids[0] if len(tax_ids) >= 1 else None
    seller_tax_id = tax_ids[1] if len(tax_ids) >= 2 else None

    amount_without_tax = None
    tax_amount = None
    total_match = TOTAL_LINE.search(t)
    if total_match:
        amount_without_tax = total_match.group(1)
        tax_amount = total_match.group(2)  # 可能是 None（普票2 的 * 场景）

    amount_in_words = None
    amount_with_tax = None
    price_tax_match = PRICE_TAX.search(t)
    if price_tax_match:
        amount_in_words = price_tax_match.group(1)
        amount_with_tax = price_tax_match.group(2)

    issuer = _first(ISSUER, t)
    remark = f"开票人:{issuer}" if issuer else None

    items = _extract_items(t)

    return {
        "invoice_type": "digital_general",
        "invoice_number": invoice_number,
        "invoice_code": None,
        "issue_date": issue_date,
        "seller": {
            "name": seller_name,
            "tax_id": seller_tax_id,
            "address": None,
            "bank": None,
        },
        "buyer": {
            "name": buyer_name,
            "tax_id": buyer_tax_id,
            "address": None,
            "bank": None,
        },
        "items": items,
        "amount_without_tax": amount_without_tax,
        "tax_amount": tax_amount,
        "amount_with_tax": amount_with_tax,
        "amount_in_words": amount_in_words,
        "remark": remark,
        "checksum": None,
        "extra": {},
        "source": {"format": "pdf", "parser_version": "0.1.0"},
    }


def _first(pat: re.Pattern[str], text: str) -> str | None:
    m = pat.search(text)
    return m.group(1).strip() if m else None


def _extract_items(text: str) -> list[dict[str, Any]]:
    """从 "项目名称 ... 税额" 表头之后、"合计" 之前的行抽取行项目。

    一期采用 best-effort：
      - 找到表头行后逐行扫描，在 "合 计" 之前停止
      - 用尾部的「金额 税率 税额」三元组定位列，再把前缀视作品名
      - 解析失败的行跳过（不抛错）
    """
    lines = text.splitlines()
    header_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if "项目名称" in line and "金" in line and "额" in line:
            header_idx = i
        elif header_idx is not None and re.match(r"\s*合\s*计", line):
            end_idx = i
            break

    if header_idx is None or end_idx is None:
        return []

    items: list[dict[str, Any]] = []
    # 尾部金额三元组：amount tax_rate tax_amount  或  amount * *
    tail_re = re.compile(r"(-?\d+\.\d{2})\s+(\d{1,2}%|\*)\s+(-?\d+\.\d{2}|\*)\s*$")
    for line in lines[header_idx + 1 : end_idx]:
        line = line.strip()
        if not line:
            continue
        m = tail_re.search(line)
        if not m:
            continue
        amount = m.group(1)
        rate = None if m.group(2) == "*" else m.group(2)
        ta = None if m.group(3) == "*" else m.group(3)
        prefix = line[: m.start()].strip()
        items.append(
            {
                "name": prefix or None,
                "spec": None,
                "unit": None,
                "quantity": None,
                "unit_price": None,
                "amount": amount,
                "tax_rate": rate,
                "tax_amount": ta,
            }
        )
    return items
