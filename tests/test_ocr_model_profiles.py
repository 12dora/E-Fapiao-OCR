from app.ocr_model_profiles import (
    DEFAULT_CNOCR_MODEL_PROFILE,
    available_profile_payload,
    resolve_cnocr_model_profile,
)


def test_default_cnocr_profile_is_invoice_lite():
    profile = resolve_cnocr_model_profile(DEFAULT_CNOCR_MODEL_PROFILE)
    assert profile.name == "invoice-lite"
    assert profile.det_model_name == "ch_PP-OCRv5_det"
    assert profile.rec_model_name == "doc-densenet_lite_136-gru"
    assert profile.det_model_backend == "onnx"
    assert profile.rec_model_backend == "onnx"


def test_cnocr_profile_aliases():
    assert resolve_cnocr_model_profile("doc").name == "invoice-lite"
    assert resolve_cnocr_model_profile("default").name == "invoice-lite"


def test_cnocr_profile_payload_lists_selection_options():
    payload = available_profile_payload()
    assert set(payload) >= {"invoice-lite", "general-lite", "scene-lite", "mobile-lite"}
    assert payload["mobile-lite"]["rec_model"] == "ch_ppocr_mobile_v2.0"


def test_unknown_cnocr_profile_is_rejected():
    try:
        resolve_cnocr_model_profile("unknown")
    except ValueError as e:
        assert "invoice-lite" in str(e)
    else:
        raise AssertionError("unknown profile should be rejected")
