"""航空运输电子客票行程单 extractor（OFD/XBRL）。"""

from __future__ import annotations

from typing import Any


def extract(fields: dict[str, str]) -> dict[str, Any]:
    invoice_number = fields.get("ElectronicInvoiceAirTransportReceiptNumber")
    issue_date = _date(fields.get("IssueDate"))
    depart_time = _datetime(fields.get("CarrierDate"), fields.get("DepartureTime"))
    amount_without_tax = fields.get("Fare")
    tax_amount = fields.get("VatTaxAmount")
    amount_with_tax = fields.get("TotalAmount")

    extra = {
        "air_itinerary": {
            "passenger_name": fields.get("PassengerName"),
            "id_no_masked": fields.get("ValidIdNumber"),
            "e_ticket_number": fields.get("ETicketNumber"),
            "flight_no": fields.get("Flight"),
            "carrier": fields.get("Carrier"),
            "cabin_class": fields.get("Class"),
            "from_station": fields.get("DepartureStation"),
            "to_station": fields.get("DestinationStation"),
            "depart_time": depart_time,
            "fare": amount_without_tax,
            "fuel_surcharge": fields.get("FuelSurcharge"),
            "civil_aviation_fund": fields.get("CivilAviationDevelopmentFund"),
            "other_taxes": fields.get("OtherTaxes"),
            "tax_rate": _tax_rate(fields.get("VatRate")),
        }
    }

    return {
        "invoice_type": "air_itinerary",
        "invoice_number": invoice_number,
        "invoice_code": None,
        "issue_date": issue_date,
        "seller": {
            "name": fields.get("NameOfSeller"),
            "tax_id": fields.get("UnifiedSocialCreditCodeOfSeller"),
            "address": None,
            "bank": None,
        },
        "buyer": {
            "name": fields.get("NameOfPurchaser"),
            "tax_id": fields.get("UnifiedSocialCreditCodeOfPurchaser"),
            "address": None,
            "bank": None,
        },
        "items": [
            {
                "name": "航空运输电子客票行程单",
                "spec": fields.get("Flight"),
                "unit": "张",
                "quantity": "1",
                "unit_price": amount_with_tax,
                "amount": amount_with_tax,
                "tax_rate": _tax_rate(fields.get("VatRate")),
                "tax_amount": tax_amount,
            }
        ],
        "amount_without_tax": amount_without_tax,
        "tax_amount": tax_amount,
        "amount_with_tax": amount_with_tax,
        "amount_in_words": None,
        "remark": _remark(fields),
        "checksum": fields.get("VerificationCode"),
        "extra": extra,
        "source": {"format": "ofd", "parser_version": "0.1.0"},
    }


def _date(value: str | None) -> str | None:
    return value if value and len(value) == 10 else None


def _datetime(date: str | None, time: str | None) -> str | None:
    if not date or not time:
        return None
    return f"{date} {time}:00"


def _tax_rate(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return f"{float(value):.2f}"
    except ValueError:
        return value


def _remark(fields: dict[str, str]) -> str | None:
    parts = []
    if fields.get("ETicketNumber"):
        parts.append(f"电子客票号:{fields['ETicketNumber']}")
    if fields.get("Endorsement"):
        parts.append(f"签注:{fields['Endorsement']}")
    return "；".join(parts) or None
