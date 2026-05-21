from app.errors import ParseFailed
from app.extractors import digital_general, digital_special, rail_12306
from app.extractors.version_adapter import select_extractor


def test_select_digital_general_fullwidth():
    fn = select_extractor("电子发票（普通发票）\n发票号码:...")
    assert fn is digital_general.extract


def test_select_digital_general_halfwidth():
    fn = select_extractor("电子发票(普通发票)\n发票号码:...")
    assert fn is digital_general.extract


def test_select_legacy_general_invoice_by_fields():
    text = """
    发票代码: 144032309110
    发票号码: 40350564
    购买方 名称: 测试采购科技有限公司
    货物或应税劳务、服务名称 规格型号 单位 数量 单价 金额 税率 税额
    合 计 2862.38 28.62
    价税合计(大写) 贰仟捌佰玖拾壹元整 (小写) ￥2891.00
    销货方 名称: 测试销售服务有限公司
    """
    fn = select_extractor(text)
    assert fn is digital_general.extract


def test_select_digital_special():
    fn = select_extractor("电子发票(增值税专用发票)\n...")
    assert fn is digital_special.extract


def test_select_rail_12306():
    fn = select_extractor("电子客票\n中国铁路祝您旅途愉快")
    assert fn is rail_12306.extract


def test_fallback_when_unknown():
    fn = select_extractor("一些不相关的文字")
    # fallback 返回的是 lambda；没有 QR payload 时直接调用应抛 ParseFailed
    try:
        fn("x")
    except ParseFailed:
        pass
    else:
        raise AssertionError("fallback 应抛 ParseFailed")


def test_fallback_with_qr_payload():
    fn = select_extractor(
        "一些不相关的文字",
        qr_payload="01,10,033002100111,26317000001791661472,211.00,20260517,12345678901234567890",
    )
    raw = fn("x")
    assert raw["invoice_type"] == "digital_general"
    assert raw["invoice_number"] == "26317000001791661472"
    assert raw["invoice_code"] == "033002100111"
    assert raw["issue_date"] == "2026-05-17"
    assert raw["amount_with_tax"] == "211.00"
    assert raw["checksum"] == "12345678901234567890"
