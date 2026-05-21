"""航空运输电子客票行程单 extractor（OCR key-value 文本）。"""

from __future__ import annotations

import re
from typing import Any


def extract(text: str) -> dict[str, Any]:
    fields = _parse_key_values(text)
    flight = _first_flight_item(text)

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
            "name": _get(fields, "Issuer", "Seller", "销售方"),
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
