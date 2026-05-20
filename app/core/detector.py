"""FormatDetector —— 根据 magic bytes / 后缀识别文件格式。

PDF:   b"%PDF-"
OFD:   ZIP 容器，内部含 OFD.xml
IMAGE: JPEG (FF D8 FF) / PNG (89 50 4E 47) / ...

TODO: detect(content: bytes, filename_hint: str | None) -> Literal["pdf","ofd","image","unknown"]
"""

from typing import Literal

FileFormat = Literal["pdf", "ofd", "image", "unknown"]


def detect(content: bytes, filename_hint: str | None = None) -> FileFormat:
    raise NotImplementedError
