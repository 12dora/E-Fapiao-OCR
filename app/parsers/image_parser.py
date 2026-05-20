"""ImageParser —— 一期占位。

路由层捕获 NotImplementedError → 501 not_implemented。
"""

from typing import Any

from app.parsers.base import Parser


class ImageParser(Parser):
    def parse(self, content: bytes) -> dict[str, Any]:
        raise NotImplementedError("图片 OCR 将在 M5 阶段实装")
