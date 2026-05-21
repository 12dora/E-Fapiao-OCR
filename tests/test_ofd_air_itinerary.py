from pathlib import Path

import pytest

from app.sdk import parse_invoice

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "docs" / "sample" / "Itinerary"


def _cases() -> list[Path]:
    if not SAMPLE_DIR.is_dir():
        return []
    return sorted(SAMPLE_DIR.glob("*.ofd"))


@pytest.mark.parametrize("path", _cases(), ids=lambda path: path.name)
def test_ofd_air_itinerary_samples(path: Path) -> None:
    data = parse_invoice(path.read_bytes())
    air = data["extra"]["air_itinerary"]

    assert data["document_type"] == "ofd-air-itinerary"
    assert data["invoice_type"] == "air_itinerary"
    assert data["source"]["format"] == "ofd"
    assert data["source"]["extracted_by"] == "text_layer"
    assert data["invoice_number"]
    assert data["issue_date"]
    assert data["buyer"]["name"]
    assert data["buyer"]["tax_id"]
    assert data["seller"]["name"]
    assert data["amount_without_tax"]
    assert data["tax_amount"]
    assert data["amount_with_tax"]
    assert data["items"]
    assert air["passenger_name"]
    assert air["id_no_masked"]
    assert air["e_ticket_number"]
    assert air["flight_no"]
    assert air["from_station"]
    assert air["to_station"]
    assert air["depart_time"]


def test_ofd_air_itinerary_detects_by_content_not_filename():
    cases = _cases()
    if not cases:
        pytest.skip("OFD 行程单样本缺失")

    data = parse_invoice(cases[0].read_bytes(), hint_type="ofd")
    assert data["document_type"] == "ofd-air-itinerary"
    assert data["invoice_type"] == "air_itinerary"
