from app.extractors import digital_general, digital_special, rail_12306
from app.extractors.version_adapter import select_extractor


def test_select_digital_general_fullwidth():
    fn = select_extractor("电子发票（普通发票）\n发票号码:...")
    assert fn is digital_general.extract


def test_select_digital_general_halfwidth():
    fn = select_extractor("电子发票(普通发票)\n发票号码:...")
    assert fn is digital_general.extract


def test_select_digital_special():
    fn = select_extractor("电子发票(增值税专用发票)\n...")
    assert fn is digital_special.extract


def test_select_rail_12306():
    fn = select_extractor("电子客票\n中国铁路祝您旅途愉快")
    assert fn is rail_12306.extract


def test_fallback_when_unknown():
    fn = select_extractor("一些不相关的文字")
    # fallback 返回的是 lambda；直接调用应抛 NotImplementedError
    try:
        fn("x")
    except NotImplementedError:
        pass
    else:
        raise AssertionError("fallback 应抛 NotImplementedError")
