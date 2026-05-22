"""VersionAdapter —— 按版式分发到对应 extractor。

识别策略：关键字优先 → 二维码兜底。

兼容性处理：
  - 全/半角括号统一
  - 一些 PDF 把 "子" 渲染成康熙部首 "⼦" (U+2F26)，先 normalize
  - 识别用子串匹配（"增值税专用发票" / "普通发票" / "电子客票"），不强制 "电子发票" 前缀
"""

from __future__ import annotations

from collections.abc import Callable

from app.extractors import air_itinerary_ocr, digital_general, digital_special, fallback, rail_12306

# 已知的字符替换（康熙部首 → 中文常用字）
_NORMALIZE = str.maketrans({
    "⼦": "子",
    "⼈": "人",
    "⽉": "月",
    "⽇": "日",
    "（": "(",
    "）": ")",
})


def _normalize(text: str) -> str:
    translated = text.translate(_NORMALIZE)
    return "".join(translated.split())


def select_extractor(text: str, qr_payload: str | None = None) -> Callable[[str], dict]:
    n = _normalize(text)

    # 文本层关键字识别
    if _is_air_itinerary_ocr(n):
        return air_itinerary_ocr.extract
    if "电子客票" in n or "中国铁路" in n:
        return rail_12306.extract
    if "增值税专用发票" in n:
        return digital_special.extract
    if (
        "普通发票" in n
        or "通用(电子)发票" in n
        or ("电子发票" in n and "发票号码" in n)
        or _is_general_invoice_ocr(n)
        or _is_legacy_general_invoice(n)
    ):
        return digital_general.extract

    # 二维码 payload 兜底（M2 暂未启用，但保留路径）
    if qr_payload:
        # 数电发票二维码 payload 通常以版本号或固定前缀开头；具体格式留待 fallback 处理
        return lambda t: fallback.extract(qr_payload, text=t)

    return lambda t: fallback.extract(None, text=t)


def _is_legacy_general_invoice(normalized_text: str) -> bool:
    core_markers = (
        "发票代码" in normalized_text
        and "发票号码" in normalized_text
        and ("价税合计" in normalized_text or "合计" in normalized_text)
    )
    party_markers = (
        "购买方" in normalized_text
        or "购方" in normalized_text
        or "销售方" in normalized_text
        or "销货方" in normalized_text
    )
    item_markers = "货物或应税劳务" in normalized_text or "服务名称" in normalized_text
    return core_markers and party_markers and item_markers and "专用发票" not in normalized_text


def _is_air_itinerary_ocr(normalized_text: str) -> bool:
    if "机票行程单" in normalized_text or "航空运输电子客票行程单" in normalized_text:
        return True
    markers = (
        "旅客姓名",
        "有效身份证件号码",
        "承运人",
        "航班号",
        "电子客票号码",
        "燃油附加费",
        "民航发展基金",
        "国内国际标识",
    )
    return sum(marker in normalized_text for marker in markers) >= 4


def _is_general_invoice_ocr(normalized_text: str) -> bool:
    if "专用发票" in normalized_text:
        return False
    core = "发票号码" in normalized_text and "开票日期" in normalized_text
    party = "纳税人识别号" in normalized_text or "统一社会信用代码" in normalized_text
    totals = "价税合计" in normalized_text or "合计" in normalized_text
    items = "项目名称" in normalized_text or "税率" in normalized_text
    return core and party and totals and items
