"""Pydantic 模型 —— 对应 DESIGN.md §5/§6 的请求与响应契约。

字段命名严格遵循 DESIGN.md §6：
  - 金额统一字符串
  - 日期 YYYY-MM-DD
  - 缺字段一律 null（不省略键）
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

InvoiceType = Literal["digital_general", "digital_special", "rail_12306"]
FileFormat = Literal["pdf", "ofd", "image"]
ExtractedBy = Literal["text_layer", "qrcode", "ocr"]


class Party(BaseModel):
    name: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    bank: Optional[str] = None


class Item(BaseModel):
    name: Optional[str] = None
    spec: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[str] = None
    unit_price: Optional[str] = None
    amount: Optional[str] = None
    tax_rate: Optional[str] = None
    tax_amount: Optional[str] = None


class RailExtra(BaseModel):
    passenger_name: Optional[str] = None
    id_no_masked: Optional[str] = None
    train_no: Optional[str] = None
    from_station: Optional[str] = None
    to_station: Optional[str] = None
    depart_time: Optional[str] = None
    seat_type: Optional[str] = None


class Extra(BaseModel):
    rail_12306: Optional[RailExtra] = None


class Source(BaseModel):
    format: FileFormat
    parser_version: str
    extracted_by: ExtractedBy


class InvoiceData(BaseModel):
    invoice_type: InvoiceType
    invoice_number: Optional[str] = None
    invoice_code: Optional[str] = None
    issue_date: Optional[str] = None
    seller: Party = Field(default_factory=Party)
    buyer: Party = Field(default_factory=Party)
    items: list[Item] = Field(default_factory=list)
    amount_without_tax: Optional[str] = None
    tax_amount: Optional[str] = None
    amount_with_tax: Optional[str] = None
    amount_in_words: Optional[str] = None
    remark: Optional[str] = None
    checksum: Optional[str] = None
    extra: Extra = Field(default_factory=Extra)
    source: Source


class ParseResponse(BaseModel):
    request_id: str
    status: Literal["ok"]
    format: FileFormat
    invoice_type: InvoiceType
    data: InvoiceData
    elapsed_ms: int


class ErrorResponse(BaseModel):
    request_id: str
    status: Literal["error"] = "error"
    code: Literal[
        "invalid_input",
        "unsupported_format",
        "parse_failed",
        "not_implemented",
        "internal_error",
    ]
    message: str


class HealthResponse(BaseModel):
    status: Literal["ok"]


class CapabilitiesResponse(BaseModel):
    version: str
    formats: dict[str, str]
    invoice_types: list[str]
