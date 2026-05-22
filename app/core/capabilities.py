"""运行时能力描述，供 HTTP / CLI 共用。"""

from __future__ import annotations

from typing import Any

from app import __version__
from app.config import settings
from app.ocr_model_profiles import available_profile_payload, bundled_model_root


def build_capabilities(config: Any = settings) -> dict[str, Any]:
    image_status = "supported" if config.image_ocr_enabled else "not_implemented"
    payload = {
        "version": __version__,
        "formats": {
            "pdf": "supported",
            "ofd": "partial_supported",
            "image": image_status,
        },
        "document_types": [
            "pdf-fapiao",
            "pdf-rail-12306",
            "ofd-air-itinerary",
            "image-air-itinerary",
            "ofd-fapiao",
            "image-fapiao",
        ],
        "invoice_types": ["digital_general", "digital_special", "rail_12306", "air_itinerary"],
        "parse_modes": {
            "ocr_mode": {
                "auto": (
                    "默认模式：PDF/OFD 优先使用规则引擎；图片或需 OCR 的路径只有在"
                    "已配置 vendor 时才使用 OCR"
                ),
                "disabled": (
                    "纯规则模式：不调用本地或在线 OCR；规则无法处理时返回 "
                    "rule_unhandled 或 not_implemented"
                ),
                "required": (
                    "要求 OCR：未配置 OCR vendor 时直接返回 not_implemented，"
                    "适合上游强制 OCR 队列"
                ),
            }
        },
    }
    if getattr(config, "ocr_vendor", "").lower() == "cnocr":
        payload["ocr"] = {
            "vendor": "cnocr",
            "model_profile": config.cnocr_model_profile,
            "det_model": config.cnocr_det_model_name,
            "rec_model": config.cnocr_rec_model_name,
            "det_backend": config.cnocr_det_model_backend,
            "rec_backend": config.cnocr_rec_model_backend,
            "bundled_models": bundled_model_root() is not None,
            "available_model_profiles": available_profile_payload(),
        }
    return payload
