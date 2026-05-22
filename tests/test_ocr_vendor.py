import sys
import types

from app.errors import ParseFailed
from app.ocr import tencent_ocr_credentials
from app.ocr.base import OcrResult, OcrTextLine
from app.ocr.factory import create_ocr_vendor
from app.ocr.vendors import cnocr_vendor
from app.ocr.vendors.http_vendor import HttpOcrVendor, _parse_payload
from app.ocr.vendors.tencent_vendor import (
    _build_headers,
    _load_credentials_file,
    _parse_response,
    _TencentConfig,
)
from app.parsers.image_parser import ImageParser


def test_ocr_vendor_disabled_by_default():
    create_ocr_vendor.cache_clear()
    try:
        create_ocr_vendor()
    except NotImplementedError as e:
        assert "未启用" in str(e)
    else:
        raise AssertionError("默认未配置 OCR vendor 时应返回 501 语义")


def test_cnocr_vendor_uses_lightweight_doc_model(monkeypatch):
    calls = {}

    class FakeSettings:
        cnocr_model_profile = "invoice-lite"
        cnocr_det_model_name = "ch_PP-OCRv5_det"
        cnocr_rec_model_name = "doc-densenet_lite_136-gru"
        cnocr_det_model_backend = "onnx"
        cnocr_rec_model_backend = "onnx"

    class FakeCnOcr:
        def __init__(self, **kwargs):
            calls["init"] = kwargs

        def ocr(self, image):
            calls["image_mode"] = image.mode
            return [
                {"text": "电子发票(普通发票)", "score": "0.99", "position": [[0, 0], [1, 0]]},
                ([[0, 10], [1, 10]], ("发票号码:26317000001791661472", 0.98)),
            ]

    class FakeImage:
        mode = "L"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def convert(self, mode):
            self.mode = mode
            return self

    fake_cnocr_module = types.SimpleNamespace(CnOcr=FakeCnOcr)
    monkeypatch.setitem(sys.modules, "cnocr", fake_cnocr_module)
    monkeypatch.setattr(cnocr_vendor, "settings", FakeSettings())
    monkeypatch.setattr(cnocr_vendor.Image, "open", lambda _: FakeImage())

    vendor = cnocr_vendor.CnOcrVendor()
    result = vendor.recognize(b"fake image bytes")

    assert calls["init"] == {
        "det_model_name": "ch_PP-OCRv5_det",
        "rec_model_name": "doc-densenet_lite_136-gru",
        "det_model_backend": "onnx",
        "rec_model_backend": "onnx",
    }
    assert calls["image_mode"] == "RGB"
    assert vendor.rec_model_name == "doc-densenet_lite_136-gru"
    assert vendor.model_profile == "invoice-lite"
    assert result.vendor == "cnocr"
    assert [line.text for line in result.lines] == [
        "电子发票(普通发票)",
        "发票号码:26317000001791661472",
    ]
    assert result.lines[0].score == 0.99


def test_http_vendor_payload_text():
    result = _parse_payload({"text": "电子发票(普通发票)\n发票号码:123"})
    assert result.vendor == "http"
    assert result.text == "电子发票(普通发票)\n发票号码:123"


def test_http_vendor_payload_lines():
    result = _parse_payload(
        {
            "lines": [
                {"text": "电子发票(普通发票)", "score": 0.99},
                {"text": "发票号码:123", "score": 0.98},
            ]
        }
    )
    assert [line.text for line in result.lines] == ["电子发票(普通发票)", "发票号码:123"]


def test_http_vendor_rejects_unsafe_url(monkeypatch):
    class FakeSettings:
        ocr_http_url = "http://127.0.0.1/ocr"
        ocr_http_allow_http = True
        ocr_http_timeout_seconds = 10
        ocr_http_headers = ""

    monkeypatch.setattr("app.ocr.vendors.http_vendor.settings", FakeSettings())
    try:
        HttpOcrVendor()
    except Exception as e:
        assert "内网" in str(e) or "本机" in str(e)
    else:
        raise AssertionError("HTTP OCR vendor 不应允许内网 URL")


def test_image_parser_uses_ocr_vendor(monkeypatch):
    class FakeVendor:
        def recognize(self, content: bytes) -> OcrResult:
            return OcrResult(
                vendor="fake",
                lines=[
                    OcrTextLine(text="电子发票(普通发票) 发票号码:26317000001791661472"),
                    OcrTextLine(text="开票日期:2026年05月17日"),
                    OcrTextLine(text="名 称 : 浙江捷发科技股份有限公司"),
                    OcrTextLine(text="名 称 : 上海捞派餐饮管理有限公司"),
                    OcrTextLine(text="统一社会信用代码/纳税人识别号:91330600597214350R"),
                    OcrTextLine(text="统一社会信用代码/纳税人识别号:91310000000000000X"),
                    OcrTextLine(text="项目名称 金 额 税率/征收率 税 额"),
                    OcrTextLine(text="*餐饮服务*餐费 199.06 6% 11.94"),
                    OcrTextLine(text="合 计 ¥199.06 ¥11.94"),
                    OcrTextLine(text="价税合计(大写) 贰佰壹拾壹圆整 (小写) ¥211.00"),
                ],
            )

    monkeypatch.setattr("app.parsers.image_parser.create_ocr_vendor", lambda: FakeVendor())

    raw = ImageParser().parse(b"fake image bytes")
    assert raw["invoice_type"] == "digital_general"
    assert raw["invoice_number"] == "26317000001791661472"
    assert raw["amount_with_tax"] == "211.00"
    assert raw["source"]["extracted_by"] == "ocr"
    assert raw["source"]["ocr_vendor"] == "fake"


def test_image_parser_rejects_short_ocr_text(monkeypatch):
    class FakeVendor:
        def recognize(self, content: bytes) -> OcrResult:
            return OcrResult(vendor="fake", lines=[OcrTextLine(text="太短")])

    monkeypatch.setattr("app.parsers.image_parser.create_ocr_vendor", lambda: FakeVendor())

    try:
        ImageParser().parse(b"fake image bytes")
    except ParseFailed:
        pass
    else:
        raise AssertionError("OCR 文本过短时应抛 ParseFailed")


def test_tencent_build_headers_contains_tc3_signature():
    config = _TencentConfig(
        secret_id="sid",
        secret_key="skey",
        token="token",
        region="ap-guangzhou",
        endpoint="ocr.tencentcloudapi.com",
        action="RecognizeGeneralInvoice",
        version="2018-11-19",
        timeout=10,
    )
    headers = _build_headers(config, '{"ImageBase64":"x"}', 1710000000)
    assert headers["Authorization"].startswith("TC3-HMAC-SHA256 Credential=sid/")
    assert headers["X-TC-Action"] == "RecognizeGeneralInvoice"
    assert headers["X-TC-Token"] == "token"


def test_tencent_credentials_file(tmp_path):
    p = tmp_path / "tencent.json"
    p.write_text(
        '{"secret_id":"sid","secret_key":"skey","token":"tok","region":"ap-shanghai"}',
        encoding="utf-8",
    )
    credentials = _load_credentials_file(str(p))
    assert credentials
    assert credentials.secret_id == "sid"
    assert credentials.secret_key == "skey"
    assert credentials.token == "tok"
    assert credentials.region == "ap-shanghai"


def test_tencent_context_credentials():
    with tencent_ocr_credentials(
        secret_id="sid",
        secret_key="skey",
        token="tok",
        region="ap-shanghai",
    ):
        from app.ocr.credentials import get_tencent_ocr_credentials

        credentials = get_tencent_ocr_credentials()
        assert credentials
        assert credentials.secret_id == "sid"
        assert credentials.secret_key == "skey"
        assert credentials.token == "tok"
        assert credentials.region == "ap-shanghai"


def test_tencent_parse_response_mixed_invoice_items():
    result = _parse_response(
        {
            "Response": {
                "MixedInvoiceItems": [
                    {"Name": "发票号码", "Value": "26317000001791661472"},
                    {"Name": "开票日期", "Value": "2026年05月17日"},
                ]
            }
        }
    )
    assert result.vendor == "tencent"
    assert result.text == "发票号码: 26317000001791661472\n开票日期: 2026年05月17日"
