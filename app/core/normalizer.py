"""Normalizer —— 字段归一化。

职责：
  - 金额：所有金额字段统一为字符串两位小数，如 "100.00"
  - 日期：统一 YYYY-MM-DD
  - 缺字段补 null（不省略键）
  - 统一全角半角、去除字符串前后空白

输入：extractor 产出的 RawInvoice（字段不规整）
输出：DESIGN.md §6 定义的统一 schema dict
"""


def normalize(raw: dict) -> dict:
    raise NotImplementedError
