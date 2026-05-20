"""库（in-process）门面 —— 给 Python 调用方直接 import 用。

设计意图（DESIGN.md §13）：
  - 这是"嵌入式"集成形态的入口。其它 Python 程序：
        from app.sdk import parse_invoice
        result = parse_invoice(pdf_bytes)
  - 与 HTTP API 等价语义：同样的 detector → parser → version_adapter → extractor → normalizer 链。
  - 错误以异常形式抛出（ParseFailed / UnsupportedFormat / NotImplementedError），
    由调用方决定怎么处理。HTTP 层负责把异常映射到 §5.4 状态码。

TODO(M1): 串起完整 pipeline 并实装。
"""

from typing import Any


def parse_invoice(content: bytes, hint_type: str | None = None) -> dict[str, Any]:
    """把发票字节流解析为 DESIGN.md §6 定义的统一 JSON dict。

    参数:
        content:    发票文件原始字节（PDF / OFD / 图片）。
        hint_type:  "pdf" | "ofd" | "image" | None(=auto)，用于跳过格式探测。

    返回:
        归一化后的 dict（结构见 DESIGN.md §6）。

    异常:
        UnsupportedFormat   不是支持的格式
        ParseFailed         能识别格式但抽不出字段
        NotImplementedError OFD / 图片 一期未实装
    """
    raise NotImplementedError
