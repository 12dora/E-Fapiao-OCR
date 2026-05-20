"""Pydantic 模型 —— 对应 DESIGN.md §5/§6 的请求与响应契约。

字段命名严格遵循 DESIGN.md §6 的统一 JSON Schema：
  - 金额统一字符串
  - 日期 YYYY-MM-DD
  - 缺字段一律 null（不省略键）

TODO: 完整实现 InvoiceData / Seller / Buyer / Item / RailExtra / ParseResponse
"""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
