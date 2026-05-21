"""FormatDetector —— 根据 magic bytes / 后缀识别文件格式。

PDF:   b"%PDF-"
OFD:   ZIP 容器（PK\x03\x04）+ 内含 OFD.xml 条目
IMAGE: JPEG (FF D8 FF) / PNG (89 50 4E 47 0D 0A 1A 0A) / GIF / WEBP
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from typing import Literal

FileFormat = Literal["pdf", "ofd", "image", "unknown"]

_JPEG = b"\xff\xd8\xff"
_PNG = b"\x89PNG\r\n\x1a\n"
_GIF87 = b"GIF87a"
_GIF89 = b"GIF89a"
_ZIP = b"PK\x03\x04"
_PDF = b"%PDF-"


def detect(content: bytes, filename_hint: str | None = None) -> FileFormat:
    if not content:
        return "unknown"

    head = content[:16]

    if head.startswith(_PDF):
        return "pdf"

    if (
        head.startswith(_JPEG)
        or head.startswith(_PNG)
        or head.startswith(_GIF87)
        or head.startswith(_GIF89)
    ):
        return "image"

    if head.startswith(_ZIP):
        # OFD 与普通 ZIP 都以 PK 开头；检查内部是否含 OFD.xml
        try:
            with zipfile.ZipFile(BytesIO(content)) as zf:
                names = {n.lower() for n in zf.namelist()}
                if "ofd.xml" in names or any(n.endswith("/ofd.xml") for n in names):
                    return "ofd"
        except zipfile.BadZipFile:
            pass

    # 兜底：根据文件名后缀提示
    if filename_hint:
        ext = filename_hint.rsplit(".", 1)[-1].lower()
        if ext == "pdf":
            return "pdf"
        if ext == "ofd":
            return "ofd"
        if ext in {"jpg", "jpeg", "png", "gif", "webp", "bmp"}:
            return "image"

    return "unknown"
