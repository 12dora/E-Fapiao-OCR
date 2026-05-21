import pytest

from app.errors import UnsupportedDocumentType
from app.sdk import parse_invoice
from tests.fixtures import sanitized


def test_ofd_invoice_text_is_detected_but_not_parsed() -> None:
    with pytest.raises(UnsupportedDocumentType, match="OFD 发票.*不在当前支持范围") as exc_info:
        parse_invoice(sanitized.make_ofd_invoice_text())

    assert exc_info.value.document_type == "ofd-fapiao"
    assert exc_info.value.invoice_type is None


def test_ofd_unknown_document_returns_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="当前仅支持航空运输电子客票行程单"):
        parse_invoice(sanitized.make_ofd_unknown())
