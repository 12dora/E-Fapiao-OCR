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
# 权威的起止站来源是中文「起站 止站」整行（两个以「站」结尾的词，中间可能夹车次），
# 而不是罗马拼音行或跨行拼凑——后者会把下一行的日期误当成到站。
STATION_LINE = re.compile(
    r"^[^\S\n]*([^\s]+站)[^\S\n]+(?:([A-Z][0-9A-Z]{1,8})[^\S\n]+)?([^\s]+站)[^\S\n]*$",
    re.MULTILINE,
)
# 紧凑单行版式 "<起站> <车次> <止站>"（站名可能不带「站」字，车次在中间）。
# 关键：分隔符用 [^\S\n] 而非 \s，绝不跨行，避免把下一行的日期误当成到站。
TRIP_INLINE = re.compile(
    r"^[^\S\n]*(\S+)[^\S\n]+([A-Z]\d{1,4}[A-Z]?)[^\S\n]+(\S+?)[^\S\n]*$", re.MULTILINE
)
# 单独成行的车次（G1655 / D3205 / K1234 等）。
TRAIN_LINE = re.compile(r"^[^\S\n]*([A-Z]\d{1,4}[A-Z]?)[^\S\n]*$", re.MULTILINE)
# 发车时间 "HH:MM开"。
DEPART_TIME = re.compile(r"(\d{1,2}):(\d{2})开")
# 发车日期：行首的 "YYYY年MM月DD日"（区别于带 "开票日期" 前缀的开票日期）。
DEPART_DATE_LINE = re.compile(r"^[^\S\n]*(\d{4})年(\d{1,2})月(\d{1,2})日", re.MULTILINE)
# 座位类型：含卧铺/无座等不以「座」结尾的种类（按最长优先排列）。
SEAT = re.compile(r"(优选一等座|商务座|特等座|一等座|二等座|无座|高级软卧|软卧|硬卧|软座|硬座)")
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
    from_station = train_no = to_station = None
    m = STATION_LINE.search(text)
    if m:
        from_station = m.group(1)
        to_station = m.group(3)
        if m.group(2):
            train_no = m.group(2)
    else:
        # 无中文「站」整行时，退回紧凑单行 "<起站> <车次> <止站>"（单行内，不跨行）。
        mi = TRIP_INLINE.search(text)
        if mi:
            from_station, train_no, to_station = mi.group(1), mi.group(2), mi.group(3)
    if train_no is None:
        mt = TRAIN_LINE.search(text)
        if mt:
            train_no = mt.group(1)
    return from_station, train_no, to_station


def _extract_depart(text: str) -> tuple[str | None, str | None]:
    seat_match = SEAT.search(text)
    seat_type = seat_match.group(1) if seat_match else None

    time_match = DEPART_TIME.search(text)
    if not time_match:
        return None, seat_type

    depart_date = None
    for m in DEPART_DATE_LINE.finditer(text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        newline = text.find("\n", m.start())
        line = text[line_start : newline if newline >= 0 else len(text)]
        if "开票日期" in line:  # 跳过开票日期行，只认发车日期
            continue
        y, mo, d = m.groups()
        depart_date = f"{y}-{int(mo):02d}-{int(d):02d}"
        break

    if depart_date is None:
        return None, seat_type
    depart_time = f"{depart_date} {int(time_match.group(1)):02d}:{time_match.group(2)}:00"
    return depart_time, seat_type


def _extract_passenger(text: str) -> tuple[str | None, str | None]:
    m = PASSENGER.search(text)
    if not m:
        return None, None
    return m.group(1), m.group(2)
