"""航空运输电子客票行程单 extractor（OCR key-value 文本）。"""

from __future__ import annotations

import re
from typing import Any


def extract(text: str) -> dict[str, Any]:
    fields = _parse_key_values(text)
    fields.update(
        {key: value for key, value in _parse_cnocr_lines(text).items() if key not in fields}
    )
    flight = _first_flight_item(text)
    if not flight:
        flight = _flight_from_fields(fields)

    invoice_number = _get(fields, "Number", "发票号码")
    issue_date = _date(_get(fields, "Date", "开票日期"))
    amount_without_tax = _get(fields, "Fare", "票价")
    tax_amount = _get(fields, "Tax", "税额")
    amount_with_tax = _get(fields, "Total", "合计", "价税合计")
    depart_time = _depart_time(flight)

    extra = {
        "air_itinerary": {
            "passenger_name": _get(fields, "UserName", "旅客姓名", "乘机人"),
            "id_no_masked": _get(fields, "UserID", "证件号码"),
            "e_ticket_number": _get(fields, "ElectronicTicketNum", "电子客票号"),
            "flight_no": flight.get("FlightNumber"),
            "carrier": flight.get("Carrier"),
            "cabin_class": flight.get("Seat"),
            "from_station": flight.get("TerminalGetOn"),
            "to_station": flight.get("TerminalGetOff"),
            "depart_time": depart_time,
            "fare": amount_without_tax,
            "fuel_surcharge": _get(fields, "FuelSurcharge", "燃油附加费"),
            "civil_aviation_fund": _get(fields, "DevelopmentFund", "民航发展基金"),
            "other_taxes": _get(fields, "OtherTax", "其他税费"),
            "tax_rate": _tax_rate(_get(fields, "TaxRate", "税率")),
        }
    }

    return {
        "document_type": "image-air-itinerary",
        "invoice_type": "air_itinerary",
        "invoice_number": invoice_number,
        "invoice_code": None,
        "issue_date": issue_date,
        "seller": {
            "name": _get(fields, "Issuer", "Seller", "销售方", "填开单位"),
            "tax_id": None,
            "address": None,
            "bank": None,
        },
        "buyer": {
            "name": _get(fields, "Buyer", "购买方名称"),
            "tax_id": _get(fields, "BuyerTaxID", "购买方税号"),
            "address": None,
            "bank": None,
        },
        "items": [
            {
                "name": "航空运输电子客票行程单",
                "spec": flight.get("FlightNumber"),
                "unit": "张",
                "quantity": "1",
                "unit_price": amount_with_tax,
                "amount": amount_with_tax,
                "tax_rate": _tax_rate(_get(fields, "TaxRate", "税率")),
                "tax_amount": tax_amount,
            }
        ],
        "amount_without_tax": amount_without_tax,
        "tax_amount": tax_amount,
        "amount_with_tax": amount_with_tax,
        "amount_in_words": None,
        "remark": _get(fields, "Endorsement", "签注"),
        "checksum": _get(fields, "VerificationCode", "校验码"),
        "extra": extra,
        "source": {"format": "image", "parser_version": "0.1.0"},
    }


def _parse_key_values(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if ": " in line:
            key, value = line.split(": ", 1)
        elif ":" in line:
            key, value = line.split(":", 1)
        else:
            continue
        key = key.strip()
        value = value.strip()
        if key and value and key not in fields:
            fields[key] = value
    return fields


def _get(fields: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        value = fields.get(key)
        if value:
            return value
    return None


def _first_flight_item(text: str) -> dict[str, str | None]:
    flight: dict[str, str | None] = {}
    for key in (
        "FlightNumber",
        "Carrier",
        "Seat",
        "TerminalGetOn",
        "TerminalGetOff",
        "DateGetOn",
        "TimeGetOn",
    ):
        m = re.search(rf"{key}[\"']?\s*[:=]\s*[\"']?([^,\"'}}]+)", text)
        if m:
            flight[key] = m.group(1).strip()
    return flight


def _parse_cnocr_lines(text: str) -> dict[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    fields: dict[str, str] = {}

    _merge_table_block(
        fields,
        lines,
        ["旅客姓名", "有效身份证件号码", "签注"],
        ["UserName", "UserID", "Endorsement"],
    )
    _merge_flight_table(fields, lines)

    amount_labels = [
        ("票价", "Fare"),
        ("燃油附加费", "FuelSurcharge"),
        ("增值税税率", "TaxRate"),
        ("增值税税额", "Tax"),
        ("民航发展基金", "DevelopmentFund"),
        ("其他税费", "OtherTax"),
        ("合计", "Total"),
    ]
    label_positions = [i for i, line in enumerate(lines) if line == "票价"]
    if label_positions:
        start = label_positions[0]
        amount_values = [
            _clean_amount(line)
            for line in lines[start + 1 : start + 30]
            if _clean_amount(line) is not None or re.fullmatch(r"\d+(?:\.\d+)?%", line)
        ]
        for (_, key), value in zip(amount_labels, amount_values, strict=False):
            if value:
                fields.setdefault(key, value)

    for line in lines:
        _merge_line_field(fields, line, "发票号码", "Number")
        _merge_line_field(fields, line, "电子客票号码", "ElectronicTicketNum")
        _merge_line_field(fields, line, "验证码", "VerificationCode")
        _merge_line_field(fields, line, "保险费", "Insurance")
        _merge_line_field(fields, line, "销售网点代号", "Seller")
        _merge_line_field(fields, line, "填开单位", "Issuer")
        _merge_line_field(fields, line, "填开日期", "Date")
        _merge_line_field(fields, line, "购买方名称", "Buyer")
        _merge_line_field(fields, line, "统一社会信用代码/纳税人识别号", "BuyerTaxID")
        if line.startswith(("自:", "自：")):
            fields.setdefault("TerminalGetOn", line.split(":", 1)[-1].split("：", 1)[-1].strip())
        if line.startswith(("至:", "至：")):
            value = line.split(":", 1)[-1].split("：", 1)[-1].strip()
            if value:
                fields.setdefault("TerminalGetOff", value)

    return fields


def _merge_table_block(
    fields: dict[str, str],
    lines: list[str],
    labels: list[str],
    keys: list[str],
) -> None:
    for idx in range(0, len(lines) - len(labels)):
        if lines[idx : idx + len(labels)] != labels:
            continue
        values: list[str] = []
        for candidate in lines[idx + len(labels) : idx + len(labels) + len(keys) + 4]:
            if candidate in labels or candidate.startswith(("自:", "自：", "至:", "至：")):
                continue
            values.append(candidate)
            if len(values) == len(keys):
                break
        for key, value in zip(keys, values, strict=False):
            fields.setdefault(key, value)
        return


def _merge_flight_table(fields: dict[str, str], lines: list[str]) -> None:
    for idx, line in enumerate(lines):
        if not line.startswith(("自:", "自：")):
            continue
        value = line.split(":", 1)[-1].split("：", 1)[-1].strip()
        if value:
            fields.setdefault("TerminalGetOn", value)

        values: list[str] = []
        for candidate in lines[idx + 1 : idx + 12]:
            if candidate.startswith(("至:", "至：")):
                break
            values.append(candidate)
        for key, value in zip(
            ["Carrier", "FlightNumber", "Seat", "DateGetOn", "TimeGetOn", "FareBasis", "Allow"],
            values,
            strict=False,
        ):
            fields.setdefault(key, value)
        return


def _clean_amount(value: str) -> str | None:
    value = value.strip()
    percent = re.fullmatch(r"\d+(?:\.\d+)?%", value)
    if percent:
        return value
    match = re.fullmatch(r"(?:CNY|¥|￥)?\s*([0-9]+(?:\.[0-9]{1,2})?)", value)
    if not match:
        return None
    return match.group(1)


def _merge_line_field(fields: dict[str, str], line: str, label: str, key: str) -> None:
    normalized = line.replace("：", ":")
    prefix = label.replace("：", ":") + ":"
    if not normalized.startswith(prefix):
        return
    value = normalized[len(prefix) :].strip()
    if value:
        fields.setdefault(key, value)


def _flight_from_fields(fields: dict[str, str]) -> dict[str, str | None]:
    return {
        "FlightNumber": _get(fields, "FlightNumber", "航班号"),
        "Carrier": _get(fields, "Carrier", "承运人"),
        "Seat": _get(fields, "Seat", "座位等级", "舱位"),
        "TerminalGetOn": _get(fields, "TerminalGetOn", "出发站"),
        "TerminalGetOff": _get(fields, "TerminalGetOff", "到达站"),
        "DateGetOn": _get(fields, "DateGetOn", "日期"),
        "TimeGetOn": _get(fields, "TimeGetOn", "时间"),
    }


def _date(value: str | None) -> str | None:
    if not value:
        return None
    m = re.fullmatch(r"(\d{4})年(\d{1,2})月(\d{1,2})日", value.strip())
    if not m:
        return value if len(value) == 10 else None
    y, mo, d = m.groups()
    return f"{y}-{int(mo):02d}-{int(d):02d}"


def _depart_time(flight: dict[str, str | None]) -> str | None:
    date = _date(flight.get("DateGetOn"))
    time = flight.get("TimeGetOn")
    if not date or not time:
        return None
    return f"{date} {time}:00"


def _tax_rate(value: str | None) -> str | None:
    if not value:
        return None
    if value.endswith("%"):
        try:
            return f"{float(value[:-1]) / 100:.2f}"
        except ValueError:
            return value
    return value
