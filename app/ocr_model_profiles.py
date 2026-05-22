"""CnOCR model profiles and packaged-model discovery."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CNOCR_MODEL_PROFILE = "invoice-lite"


@dataclass(frozen=True)
class CnOcrModelProfile:
    name: str
    det_model_name: str
    rec_model_name: str
    det_model_backend: str = "onnx"
    rec_model_backend: str = "onnx"
    description: str = ""


AVAILABLE_CNOCR_MODEL_PROFILES: dict[str, CnOcrModelProfile] = {
    "invoice-lite": CnOcrModelProfile(
        name="invoice-lite",
        det_model_name="ch_PP-OCRv5_det",
        rec_model_name="doc-densenet_lite_136-gru",
        description="默认发票 OCR 轻量模型，适合票据/文档场景",
    ),
    "general-lite": CnOcrModelProfile(
        name="general-lite",
        det_model_name="ch_PP-OCRv5_det",
        rec_model_name="densenet_lite_136-gru",
        description="通用中文轻量识别模型",
    ),
    "scene-lite": CnOcrModelProfile(
        name="scene-lite",
        det_model_name="ch_PP-OCRv5_det",
        rec_model_name="scene-densenet_lite_136-gru",
        description="场景文字轻量识别模型",
    ),
    "mobile-lite": CnOcrModelProfile(
        name="mobile-lite",
        det_model_name="ch_PP-OCRv5_det",
        rec_model_name="ch_ppocr_mobile_v2.0",
        description="PP-OCR mobile 轻量识别模型，速度优先",
    ),
}

_ALIASES = {
    "default": DEFAULT_CNOCR_MODEL_PROFILE,
    "invoice": DEFAULT_CNOCR_MODEL_PROFILE,
    "doc": DEFAULT_CNOCR_MODEL_PROFILE,
}


def resolve_cnocr_model_profile(name: str | None) -> CnOcrModelProfile:
    profile_name = (name or DEFAULT_CNOCR_MODEL_PROFILE).strip()
    profile_name = _ALIASES.get(profile_name, profile_name)
    profile = AVAILABLE_CNOCR_MODEL_PROFILES.get(profile_name)
    if profile is None:
        choices = ", ".join(sorted(AVAILABLE_CNOCR_MODEL_PROFILES))
        raise ValueError(f"未知 CnOCR 模型 profile: {name}；可选值: {choices}")
    return profile


def bundled_model_root() -> Path | None:
    """Return packaged model root when present."""
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "models")
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / "models")
    candidates.append(Path(__file__).resolve().parents[1] / "models")

    for candidate in candidates:
        if (candidate / "cnocr").is_dir() and (candidate / "cnstd").is_dir():
            return candidate
    return None


def available_profile_payload() -> dict[str, dict[str, str]]:
    return {
        name: {
            "det_model": profile.det_model_name,
            "rec_model": profile.rec_model_name,
            "det_backend": profile.det_model_backend,
            "rec_backend": profile.rec_model_backend,
            "description": profile.description,
        }
        for name, profile in AVAILABLE_CNOCR_MODEL_PROFILES.items()
    }
