"""12306 电子客票 extractor。

识别特征：
  - 出现 "电子客票" / "中国铁路"
  - 含 车次 / 起止站 / 发车时间 / 座位类型 / 旅客姓名 / 证件号（掩码）

输出：RawInvoice dict，invoice_type="rail_12306"
特有字段写入 extra.rail_12306
"""

from __future__ import annotations

import re
from typing import Any

INVOICE_NO = re.compile(r"发票号码[:：\s]*([0-9A-Za-z]+)")
ISSUE_DATE = re.compile(r"开票日期[:：\s]*(\d{4})年(\d{1,2})月(\d{1,2})日")
BUYER = re.compile(r"购买方名称[:：\s]*(.+?)\s+统一社会信用代码[:：\s]*([A-Z0-9]{15,20})")
AMOUNT = re.compile(r"[¥￥]\s*([0-9]+(?:\.[0-9]{1,2})?)")
TRIP = re.compile(r"^\s*(\S+)\s+([A-Z][0-9A-Z]{1,8})\s+(\S+)\s*$", re.MULTILINE)
DEPART = re.compile(
    r"(\d{4})年(\d{1,2})月(\d{1,2})日\s+(\d{1,2}):(\d{2})开.*?\s+([一二特商务动卧硬软无等座]+座)"
)
PASSENGER = re.compile(r"([0-9A-Z]{6,}\*{2,}[0-9A-Z]+)\s+([^\s]+)")
TICKET_NO = re.compile(r"电子客票号[:：\s]*([0-9A-Za-z]+)")


def extract(text: str, blocks: list | None = None) -> dict[str, Any]:
    invoice_number = _first(INVOICE_NO, text)
    issue_date = _extract_issue_date(text)
    buyer_name, buyer_tax_id = _extract_buyer(text)
    amount = _first(AMOUNT, text)
    from_station, train_no, to_station = _extract_trip(text)
    depart_time, seat_type = _extract_depart(text)
    id_no_masked, passenger_name = _extract_passenger(text)
    ticket_no = _first(TICKET_NO, text)

    extra = {
        "rail_12306": {
            "passenger_name": passenger_name,
            "id_no_masked": id_no_masked,
            "train_no": train_no,
            "from_station": from_station,
            "to_station": to_station,
            "depart_time": depart_time,
            "seat_type": seat_type,
        }
    }

    return {
        "invoice_type": "rail_12306",
        "invoice_number": invoice_number,
        "invoice_code": None,
        "issue_date": issue_date,
        "seller": {
            "name": "中国铁路",
            "tax_id": None,
            "address": None,
            "bank": None,
        },
        "buyer": {
            "name": buyer_name,
            "tax_id": buyer_tax_id,
            "address": None,
            "bank": None,
        },
        "items": [
            {
                "name": "铁路电子客票",
                "spec": train_no,
                "unit": "张",
                "quantity": "1",
                "unit_price": amount,
                "amount": amount,
                "tax_rate": None,
                "tax_amount": None,
            }
        ],
        "amount_without_tax": None,
        "tax_amount": None,
        "amount_with_tax": amount,
        "amount_in_words": None,
        "remark": f"电子客票号:{ticket_no}" if ticket_no else None,
        "checksum": None,
        "extra": extra,
        "source": {"format": "pdf", "parser_version": "0.1.0"},
    }


def _first(pat: re.Pattern[str], text: str) -> str | None:
    m = pat.search(text)
    return m.group(1).strip() if m else None


def _extract_issue_date(text: str) -> str | None:
    m = ISSUE_DATE.search(text)
    if not m:
        return None
    y, mo, d = m.groups()
    return f"{y}-{int(mo):02d}-{int(d):02d}"


def _extract_buyer(text: str) -> tuple[str | None, str | None]:
    m = BUYER.search(text)
    if not m:
        return None, None
    return m.group(1).strip(), m.group(2).strip()


def _extract_trip(text: str) -> tuple[str | None, str | None, str | None]:
    for m in TRIP.finditer(text):
        left, train_no, right = m.groups()
        if "站" in left or "站" in right:
            continue
        return left, train_no, right
    return None, None, None


def _extract_depart(text: str) -> tuple[str | None, str | None]:
    m = DEPART.search(text)
    if not m:
        return None, None
    y, mo, d, hour, minute, seat_type = m.groups()
    depart_time = f"{y}-{int(mo):02d}-{int(d):02d} {int(hour):02d}:{minute}:00"
    return depart_time, seat_type


def _extract_passenger(text: str) -> tuple[str | None, str | None]:
    m = PASSENGER.search(text)
    if not m:
        return None, None
    return m.group(1), m.group(2)
