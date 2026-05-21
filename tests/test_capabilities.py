from app.core.capabilities import build_capabilities


class _DisabledSettings:
    image_ocr_enabled = False


class _EnabledSettings:
    image_ocr_enabled = True


def test_capabilities_image_disabled():
    payload = build_capabilities(_DisabledSettings())
    assert payload["formats"]["pdf"] == "supported"
    assert payload["formats"]["ofd"] == "partial_supported"
    assert payload["formats"]["image"] == "not_implemented"
    assert "pdf-fapiao" in payload["document_types"]
    assert "ofd-fapiao" in payload["document_types"]
    assert "ofd-air-itinerary" in payload["document_types"]
    assert "air_itinerary" in payload["invoice_types"]
    assert "digital_general" in payload["invoice_types"]
    assert "disabled" in payload["parse_modes"]["ocr_mode"]


def test_capabilities_image_enabled():
    payload = build_capabilities(_EnabledSettings())
    assert payload["formats"]["image"] == "supported"
