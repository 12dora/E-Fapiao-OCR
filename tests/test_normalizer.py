from app.core.normalizer import normalize


def test_money_to_two_decimals():
    out = normalize(
        {
            "invoice_type": "digital_general",
            "amount_with_tax": "211",
            "source": {"format": "pdf"},
        }
    )
    assert out["amount_with_tax"] == "211.00"


def test_money_strip_currency():
    out = normalize(
        {
            "invoice_type": "digital_general",
            "tax_amount": "¥ 11.94",
            "source": {"format": "pdf"},
        }
    )
    assert out["tax_amount"] == "11.94"


def test_missing_fields_become_null_not_dropped():
    out = normalize({"invoice_type": "digital_general", "source": {"format": "pdf"}})
    # 所有 §6 字段必须在
    for key in ("invoice_number", "invoice_code", "issue_date", "remark", "checksum"):
        assert key in out and out[key] is None
    assert out["seller"] == {"name": None, "tax_id": None, "address": None, "bank": None}
    assert out["buyer"] == {"name": None, "tax_id": None, "address": None, "bank": None}
    assert out["items"] == []


def test_document_type_inferred_from_format_and_invoice_type():
    assert (
        normalize({"invoice_type": "digital_general", "source": {"format": "pdf"}})[
            "document_type"
        ]
        == "pdf-fapiao"
    )
    assert (
        normalize({"invoice_type": "digital_special", "source": {"format": "pdf"}})[
            "document_type"
        ]
        == "pdf-fapiao"
    )
    assert (
        normalize({"invoice_type": "rail_12306", "source": {"format": "pdf"}})["document_type"]
        == "pdf-rail-12306"
    )
    assert (
        normalize({"invoice_type": "air_itinerary", "source": {"format": "ofd"}})[
            "document_type"
        ]
        == "ofd-air-itinerary"
    )


def test_asterisk_treated_as_missing():
    out = normalize(
        {"invoice_type": "digital_general", "tax_amount": "*", "source": {"format": "pdf"}}
    )
    assert out["tax_amount"] is None


def test_date_passthrough():
    out = normalize(
        {
            "invoice_type": "digital_general",
            "issue_date": "2026-05-17",
            "source": {"format": "pdf"},
        }
    )
    assert out["issue_date"] == "2026-05-17"


def test_source_defaults():
    out = normalize({"invoice_type": "digital_general", "source": {"format": "pdf"}})
    assert out["source"]["format"] == "pdf"
    assert out["source"]["extracted_by"] == "text_layer"
    assert out["source"]["parser_version"]


def test_source_preserves_ocr_vendor():
    out = normalize(
        {
            "invoice_type": "digital_general",
            "source": {"format": "image", "extracted_by": "ocr", "ocr_vendor": "tencent"},
        }
    )
    assert out["source"]["ocr_vendor"] == "tencent"
