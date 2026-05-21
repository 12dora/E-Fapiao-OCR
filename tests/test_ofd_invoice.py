from pathlib import Path

import pytest

from app.errors import UnsupportedDocumentType
from app.ocr.base import OcrResult, OcrTextLine
from app.sdk import parse_invoice

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "docs" / "sample" / "ofd-fapiao"


def _cases() -> list[Path]:
    if not SAMPLE_DIR.is_dir():
        return []
    return sorted(SAMPLE_DIR.glob("*.ofd"))


class _FakeOcrVendor:
    name = "fake"

    def recognize(self, content: bytes) -> OcrResult:
        return OcrResult(vendor=self.name, lines=[OcrTextLine(text="全国统一发票监制章 电子发票")])


@pytest.mark.parametrize("path", _cases(), ids=lambda path: path.name)
def test_ofd_invoice_samples_are_detected_but_not_parsed(
    path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.parsers.ofd_parser.create_ocr_vendor", lambda: _FakeOcrVendor())

    with pytest.raises(UnsupportedDocumentType, match="OFD 发票.*不在当前支持范围") as exc_info:
        parse_invoice(path.read_bytes())
    assert exc_info.value.document_type == "ofd-fapiao"
