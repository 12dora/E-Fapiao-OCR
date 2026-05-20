"""兜底 extractor —— 优先消费二维码 payload。

数电发票二维码内容通常包含：发票号码 / 开票日期 / 金额 / 税额 / 校验码。
当文本层抽取失败时，二维码是最稳的兜底来源。
"""


def extract(qr_payload: str | None, text: str | None = None) -> dict:
    raise NotImplementedError
