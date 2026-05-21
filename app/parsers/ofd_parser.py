"""OfdParser。

当前 OFD 只做内容分类与航空运输电子客票行程单解析：
- 行程单：按 OFD 内部 XBRL/OFD XML 字段解析为结构化数据；
- 发票：按 OFD 内部字段/文本识别，但字段解析不在当前支持范围内。
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO
from typing import Any

from app.errors import ParseFailed, UnsupportedDocumentType
from app.extractors import air_itinerary
from app.ocr import create_ocr_vendor
from app.parsers.base import Parser


class OfdParser(Parser):
    def parse(self, content: bytes, *, ocr_mode: str = "auto") -> dict[str, Any]:
        package = _extract_ofd_package(content)
        fields = package.fields
        if _is_air_itinerary(fields):
            raw = air_itinerary.extract(fields)
            raw.setdefault("source", {})
            raw["source"]["extracted_by"] = "text_layer"
            return raw

        if _is_ofd_invoice(package, ocr_mode=ocr_mode):
            raise UnsupportedDocumentType(
                "已识别为 OFD 发票，但 OFD 发票解析不在当前支持范围内",
                document_type="ofd-fapiao",
            )

        raise NotImplementedError(
            "当前仅支持航空运输电子客票行程单 OFD；OFD 发票仅做类型识别，不解析字段"
        )


class _OfdPackage:
    def __init__(self) -> None:
        self.fields: dict[str, str] = {}
        self.page_text: list[tuple[float, float, str]] = []
        self.template_text: list[tuple[float, float, str]] = []
        self.images: list[bytes] = []


def _extract_ofd_package(content: bytes) -> _OfdPackage:
    try:
        with zipfile.ZipFile(BytesIO(content)) as zf:
            package = _OfdPackage()
            for name in zf.namelist():
                lower = name.lower()
                if lower.endswith((".png", ".jpg", ".jpeg")):
                    package.images.append(zf.read(name))
                    continue
                if not lower.endswith(".xml"):
                    continue
                if "/attachs/atr_" in lower:
                    _merge_xml_text(package.fields, zf.read(name))
                    continue
                if lower.endswith("/pages/page_0/content.xml"):
                    package.page_text.extend(_extract_text_codes(zf.read(name)))
                    continue
                if "/tpls/" in lower and lower.endswith("/content.xml"):
                    package.template_text.extend(_extract_text_codes(zf.read(name)))
            return package
    except zipfile.BadZipFile as e:
        raise ParseFailed("OFD 文件不是合法 ZIP 容器") from e


def _merge_xml_text(fields: dict[str, str], data: bytes) -> None:
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        text = "".join(element.itertext()).strip()
        if text and tag not in fields:
            fields[tag] = text


def _extract_text_codes(data: bytes) -> list[tuple[float, float, str]]:
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return []

    rows: list[tuple[float, float, str]] = []
    for text_object in root.iter():
        if text_object.tag.rsplit("}", 1)[-1] != "TextObject":
            continue
        boundary = text_object.attrib.get("Boundary", "")
        try:
            x, y, *_ = [float(part) for part in boundary.split()]
        except ValueError:
            x = y = 0
        text = "".join(
            "".join(text_code.itertext())
            for text_code in text_object.iter()
            if text_code.tag.rsplit("}", 1)[-1] == "TextCode"
        ).strip()
        if text:
            rows.append((y, x, text))
    return sorted(rows)


def _is_air_itinerary(fields: dict[str, str]) -> bool:
    if fields.get("ElectronicInvoiceAirTransportReceiptNumber"):
        return True
    title_text = "\n".join(fields.values())
    return "航空运输电子客票行程单" in title_text


def _is_ofd_invoice(package: _OfdPackage, *, ocr_mode: str = "auto") -> bool:
    joined_fields = "\n".join(package.fields.values())
    joined_text = "\n".join(text for _, _, text in [*package.template_text, *package.page_text])
    haystack = f"{joined_fields}\n{joined_text}"
    invoice_markers = (
        "电子发票",
        "普通发票",
        "专用发票",
        "发票号码",
        "InvoiceNumber",
        "InvoiceCode",
        "TotalTax-includedAmount",
    )
    if any(marker in haystack for marker in invoice_markers):
        return True
    if ocr_mode == "disabled":
        return False
    return _is_invoice_by_embedded_image(package.images, invoice_markers)


def _is_invoice_by_embedded_image(images: list[bytes], invoice_markers: tuple[str, ...]) -> bool:
    if not images:
        return False
    try:
        vendor = create_ocr_vendor()
    except NotImplementedError:
        return False

    for image in images:
        try:
            text = vendor.recognize(image).text
        except Exception:
            continue
        if any(marker in text for marker in invoice_markers):
            return True
    return False
