"""OfdParser —— 一期占位。

路由层捕获 NotImplementedError → 501 not_implemented。
"""

from typing import Any

from app.parsers.base import Parser


class OfdParser(Parser):
    def parse(self, content: bytes) -> dict[str, Any]:
        raise NotImplementedError("OFD 解析将在 M4 阶段实装")
