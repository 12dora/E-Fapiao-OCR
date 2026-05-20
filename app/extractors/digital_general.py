"""数电普票 extractor。

识别特征：
  - 标题包含 "电子发票（普通发票）"
  - 二维码 payload 前缀 / 字段排布

输出：RawInvoice dict，invoice_type="digital_general"
"""


def extract(text: str, blocks: list | None = None) -> dict:
    raise NotImplementedError
