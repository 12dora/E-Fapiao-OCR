"""12306 电子客票 extractor。

识别特征：
  - 出现 "电子客票" / "中国铁路"
  - 含 车次 / 起止站 / 发车时间 / 座位类型 / 旅客姓名 / 证件号（掩码）

输出：RawInvoice dict，invoice_type="rail_12306"
特有字段写入 extra.rail_12306
"""


def extract(text: str, blocks: list | None = None) -> dict:
    raise NotImplementedError
