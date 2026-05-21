"""Pydantic 模型 —— 对应 DESIGN.md §5/§6 的请求与响应契约。

字段命名严格遵循 DESIGN.md §6：
  - 金额统一字符串
  - 日期 YYYY-MM-DD
  - 缺字段一律 null（不省略键）
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DocumentType = Literal[
    "pdf-fapiao",
    "ofd-fapiao",
    "pdf-rail-12306",
    "ofd-air-itinerary",
    "image-air-itinerary",
    "image-fapiao",
]
InvoiceType = Literal["digital_general", "digital_special", "rail_12306", "air_itinerary"]
FileFormat = Literal["pdf", "ofd", "image"]
ExtractedBy = Literal["text_layer", "qrcode", "ocr"]
OcrMode = Literal["auto", "disabled", "required"]


class Party(BaseModel):
    name: str | None = None
    tax_id: str | None = None
    address: str | None = None
    bank: str | None = None


class Item(BaseModel):
    name: str | None = None
    spec: str | None = None
    unit: str | None = None
    quantity: str | None = None
    unit_price: str | None = None
    amount: str | None = None
    tax_rate: str | None = None
    tax_amount: str | None = None


class RailExtra(BaseModel):
    passenger_name: str | None = None
    id_no_masked: str | None = None
    train_no: str | None = None
    from_station: str | None = None
    to_station: str | None = None
    depart_time: str | None = None
    seat_type: str | None = None


class AirItineraryExtra(BaseModel):
    passenger_name: str | None = None
    id_no_masked: str | None = None
    e_ticket_number: str | None = None
    flight_no: str | None = None
    carrier: str | None = None
    cabin_class: str | None = None
    from_station: str | None = None
    to_station: str | None = None
    depart_time: str | None = None
    fare: str | None = None
    fuel_surcharge: str | None = None
    civil_aviation_fund: str | None = None
    other_taxes: str | None = None
    tax_rate: str | None = None


class Extra(BaseModel):
    rail_12306: RailExtra | None = None
    air_itinerary: AirItineraryExtra | None = None


class Source(BaseModel):
    format: FileFormat
    parser_version: str
    extracted_by: ExtractedBy
    ocr_vendor: str | None = None


class EngineStatus(BaseModel):
    rule_engine: Literal["attempted", "skipped"] = "attempted"
    ocr_mode: OcrMode = "auto"
    ocr_enabled: bool = False
    ocr_used: bool = False
    ocr_required: bool = False
    ocr_vendor: str | None = None


class InvoiceData(BaseModel):
    document_type: DocumentType
    invoice_type: InvoiceType
    invoice_number: str | None = None
    invoice_code: str | None = None
    issue_date: str | None = None
    seller: Party = Field(default_factory=Party)
    buyer: Party = Field(default_factory=Party)
    items: list[Item] = Field(default_factory=list)
    amount_without_tax: str | None = None
    tax_amount: str | None = None
    amount_with_tax: str | None = None
    amount_in_words: str | None = None
    remark: str | None = None
    checksum: str | None = None
    extra: Extra = Field(default_factory=Extra)
    source: Source


class ParseResponse(BaseModel):
    request_id: str
    status: Literal["ok"]
    format: FileFormat
    document_type: DocumentType
    invoice_type: InvoiceType
    data: InvoiceData
    engine: EngineStatus
    elapsed_ms: int


ErrorCode = Literal[
    "invalid_input",
    "unsupported_format",
    "rule_unhandled",
    "parse_failed",
    "not_implemented",
    "internal_error",
]


class ErrorResponse(BaseModel):
    request_id: str
    status: Literal["error"] = "error"
    code: ErrorCode
    message: str
    document_type: DocumentType | None = None
    invoice_type: InvoiceType | None = None
    engine: EngineStatus | None = None


class BatchParseItem(BaseModel):
    index: int
    filename: str | None = None
    status: Literal["ok", "error"]
    format: FileFormat | None = None
    document_type: DocumentType | None = None
    invoice_type: InvoiceType | None = None
    data: InvoiceData | None = None
    code: ErrorCode | None = None
    message: str | None = None
    engine: EngineStatus
    elapsed_ms: int


class BatchParseResponse(BaseModel):
    request_id: str
    status: Literal["ok"]
    total: int
    succeeded: int
    failed: int
    items: list[BatchParseItem]
    elapsed_ms: int


class HealthResponse(BaseModel):
    status: Literal["ok"]


class CapabilitiesResponse(BaseModel):
    version: str
    formats: dict[str, str]
    document_types: list[str]
    invoice_types: list[str]
    parse_modes: dict[str, dict[str, str]]
