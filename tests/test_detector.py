from app.core.detector import detect
from tests.fixtures.sanitized import make_ofd_air_itinerary


def test_pdf_magic():
    assert detect(b"%PDF-1.7\nfoo") == "pdf"


def test_jpeg_magic():
    assert detect(b"\xff\xd8\xff\xe0foo") == "image"


def test_png_magic():
    assert detect(b"\x89PNG\r\n\x1a\nfoo") == "image"


def test_ofd_zip_magic_and_ofd_xml():
    assert detect(make_ofd_air_itinerary()) == "ofd"


def test_unknown():
    assert detect(b"junk") == "unknown"
    assert detect(b"") == "unknown"


def test_filename_hint_fallback():
    assert detect(b"random", filename_hint="x.pdf") == "pdf"
    assert detect(b"random", filename_hint="x.jpg") == "image"
