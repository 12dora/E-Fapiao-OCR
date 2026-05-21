from app.sdk import parse_invoice
from tests.fixtures import sanitized


def test_ofd_air_itinerary_sanitized_container_parses() -> None:
    data = parse_invoice(sanitized.make_ofd_air_itinerary())
    air = data["extra"]["air_itinerary"]

    assert data["document_type"] == "ofd-air-itinerary"
    assert data["invoice_type"] == "air_itinerary"
    assert data["source"]["format"] == "ofd"
    assert data["source"]["extracted_by"] == "text_layer"
    assert data["invoice_number"] == "AIR000000000001"
    assert data["issue_date"] == "2025-07-04"
    assert data["buyer"]["name"] == "脱敏采购科技有限公司"
    assert data["buyer"]["tax_id"] == "91110000000000001A"
    assert data["seller"]["name"] == "脱敏航空有限公司"
    assert data["amount_without_tax"] == "550.46"
    assert data["tax_amount"] == "49.54"
    assert data["amount_with_tax"] == "610.46"
    assert data["items"][0]["name"] == "航空运输电子客票行程单"
    assert air["passenger_name"] == "测试旅客"
    assert air["id_no_masked"] == "110000********001X"
    assert air["e_ticket_number"] == "7812345678901"
    assert air["flight_no"] == "CA1234"
    assert air["from_station"] == "脱敏机场"
    assert air["to_station"] == "测试机场"
    assert air["depart_time"] == "2025-07-05 08:15:00"


def test_ofd_air_itinerary_detects_by_content_not_filename() -> None:
    data = parse_invoice(sanitized.make_ofd_air_itinerary(), hint_type="ofd")
    assert data["document_type"] == "ofd-air-itinerary"
    assert data["invoice_type"] == "air_itinerary"
