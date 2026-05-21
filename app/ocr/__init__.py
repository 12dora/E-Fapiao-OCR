"""OCR vendor 抽象层。

ImageParser 只依赖本包暴露的统一接口；CnOCR、本地模型或第三方 API 都是 vendor。
"""

from app.ocr.base import OcrResult, OcrTextLine, OcrVendor
from app.ocr.credentials import TencentOcrCredentials, tencent_ocr_credentials
from app.ocr.factory import create_ocr_vendor

__all__ = [
    "OcrResult",
    "OcrTextLine",
    "OcrVendor",
    "TencentOcrCredentials",
    "create_ocr_vendor",
    "tencent_ocr_credentials",
]
