import pytest

from app.core.url_security import validate_public_http_url
from app.errors import InvalidInput


def test_rejects_http_by_default():
    with pytest.raises(InvalidInput):
        validate_public_http_url("http://example.com/ocr")


def test_allows_http_when_explicitly_enabled():
    assert (
        validate_public_http_url("http://8.8.8.8/ocr", allow_http=True)
        == "http://8.8.8.8/ocr"
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://localhost/ocr",
        "https://127.0.0.1/ocr",
        "https://10.0.0.1/ocr",
        "https://172.16.0.1/ocr",
        "https://192.168.1.1/ocr",
        "https://[::1]/ocr",
        "ftp://example.com/ocr",
    ],
)
def test_rejects_unsafe_urls(url: str):
    with pytest.raises(InvalidInput):
        validate_public_http_url(url)


def test_allows_public_https():
    assert validate_public_http_url("https://8.8.8.8/ocr") == "https://8.8.8.8/ocr"
