"""数电专票 extractor。

识别特征：
  - 标题包含 "电子发票（增值税专用发票）"
  - 含购买方/销售方/税号/税率/税额行项目

输出：RawInvoice dict，invoice_type="digital_special"
"""


def extract(text: str, blocks: list | None = None) -> dict:
    raise NotImplementedError
