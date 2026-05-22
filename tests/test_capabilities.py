from app.core.capabilities import build_capabilities


class _DisabledSettings:
    image_ocr_enabled = False


class _EnabledSettings:
    image_ocr_enabled = True


class _CnOcrSettings:
    image_ocr_enabled = True
    ocr_vendor = "cnocr"
    cnocr_model_profile = "invoice-lite"
    cnocr_det_model_name = "ch_PP-OCRv5_det"
    cnocr_rec_model_name = "doc-densenet_lite_136-gru"
    cnocr_det_model_backend = "onnx"
    cnocr_rec_model_backend = "onnx"


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


def test_capabilities_includes_cnocr_model_profiles():
    payload = build_capabilities(_CnOcrSettings())
    assert payload["ocr"]["vendor"] == "cnocr"
    assert payload["ocr"]["model_profile"] == "invoice-lite"
    assert payload["ocr"]["rec_model"] == "doc-densenet_lite_136-gru"
    assert "invoice-lite" in payload["ocr"]["available_model_profiles"]
    assert "mobile-lite" in payload["ocr"]["available_model_profiles"]
