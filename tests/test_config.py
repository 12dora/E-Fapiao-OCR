"""Settings.from_env 的环境变量映射测试。

覆盖安全相关配置（鉴权、上传上限、SSRF/明文开关）以及错误配置容错，
避免 env→字段 的接线在重构中被静默改坏。
"""

from __future__ import annotations

import pytest

from app.config import Settings
from app.ocr_model_profiles import resolve_cnocr_model_profile

_ENV_KEYS = [
    "EFAPIAO_API_KEY",
    "EFAPIAO_MAX_FILE_BYTES",
    "EFAPIAO_MAX_REQUEST_BYTES",
    "EFAPIAO_PORT",
    "EFAPIAO_FORWARD_ALLOW_HTTP",
    "EFAPIAO_OCR_HTTP_ALLOW_HTTP",
    "EFAPIAO_CNOCR_MODEL_PROFILE",
    "EFAPIAO_CNOCR_DET_MODEL",
    "EFAPIAO_CNOCR_REC_MODEL",
    "EFAPIAO_TENCENT_SECRET_ID",
    "TENCENTCLOUD_SECRET_ID",
]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_defaults_are_secure() -> None:
    settings = Settings.from_env()
    assert settings.api_key == ""
    assert settings.auth_enabled is False
    assert settings.forward_allow_http is False
    assert settings.ocr_http_allow_http is False
    assert settings.max_file_bytes == 10 * 1024 * 1024


def test_api_key_enables_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EFAPIAO_API_KEY", "secret")
    settings = Settings.from_env()
    assert settings.api_key == "secret"
    assert settings.auth_enabled is True


def test_allow_http_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EFAPIAO_FORWARD_ALLOW_HTTP", "true")
    monkeypatch.setenv("EFAPIAO_OCR_HTTP_ALLOW_HTTP", "true")
    settings = Settings.from_env()
    assert settings.forward_allow_http is True
    assert settings.ocr_http_allow_http is True


def test_max_file_bytes_and_request_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EFAPIAO_MAX_FILE_BYTES", "2048")
    settings = Settings.from_env()
    assert settings.max_file_bytes == 2048
    # 请求上限必须严格大于单文件上限，否则单个满额文件会被误拒。
    assert settings.max_request_bytes > settings.max_file_bytes


def test_malformed_numeric_env_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EFAPIAO_PORT", "not_a_number")
    monkeypatch.setenv("EFAPIAO_MAX_FILE_BYTES", "")
    settings = Settings.from_env()
    assert settings.port == 8000
    assert settings.max_file_bytes == 10 * 1024 * 1024


def test_unknown_cnocr_profile_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EFAPIAO_CNOCR_MODEL_PROFILE", "does-not-exist")
    settings = Settings.from_env()
    default = resolve_cnocr_model_profile(None)
    assert settings.cnocr_det_model_name == default.det_model_name
    assert settings.cnocr_rec_model_name == default.rec_model_name


def test_explicit_cnocr_model_override_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EFAPIAO_CNOCR_MODEL_PROFILE", "does-not-exist")
    monkeypatch.setenv("EFAPIAO_CNOCR_DET_MODEL", "custom-det")
    monkeypatch.setenv("EFAPIAO_CNOCR_REC_MODEL", "custom-rec")
    settings = Settings.from_env()
    assert settings.cnocr_det_model_name == "custom-det"
    assert settings.cnocr_rec_model_name == "custom-rec"


def test_tencentcloud_env_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TENCENTCLOUD_SECRET_ID", "tc-generic")
    assert Settings.from_env().tencent_secret_id == "tc-generic"
    monkeypatch.setenv("EFAPIAO_TENCENT_SECRET_ID", "efapiao-specific")
    assert Settings.from_env().tencent_secret_id == "efapiao-specific"
