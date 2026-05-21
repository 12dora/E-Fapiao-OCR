"""OCR vendor 工厂。

默认不启用 OCR；配置 EFAPIAO_OCR_VENDOR=cnocr/http/tencent 后才实例化对应 vendor。
"""

from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.ocr.base import OcrVendor
from app.ocr.vendors.cnocr_vendor import CnOcrVendor
from app.ocr.vendors.http_vendor import HttpOcrVendor
from app.ocr.vendors.tencent_vendor import TencentOcrVendor


@lru_cache(maxsize=1)
def create_ocr_vendor() -> OcrVendor:
    vendor = settings.ocr_vendor.lower()
    if vendor in {"", "none", "disabled"}:
        raise NotImplementedError("图片 OCR 未启用，请配置 EFAPIAO_OCR_VENDOR")
    if vendor == "cnocr":
        return CnOcrVendor()
    if vendor == "http":
        return HttpOcrVendor()
    if vendor == "tencent":
        return TencentOcrVendor()
    raise NotImplementedError(f"未知 OCR vendor: {settings.ocr_vendor}")
