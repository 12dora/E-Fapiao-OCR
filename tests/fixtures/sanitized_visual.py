"""Render commit-safe invoice abstractions into OCR-like visual inputs."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def render_visual_png(visual: dict[str, Any], *, scale: float = 2.0) -> bytes:
    if visual["kind"] == "pdf_text_layout":
        return _render_pdf_text_layout_png(visual, scale=scale)
    if visual["kind"] == "image_text_layout":
        return _render_image_text_layout_png(visual)
    if visual["kind"] == "semantic_text":
        return _render_semantic_text_png(visual["text"])
    raise NotImplementedError(f"Unsupported visual fixture kind: {visual['kind']}")


def render_visual_pdf(visual: dict[str, Any], *, scale: float = 2.0) -> bytes:
    """Render a visual abstraction as an image-only PDF for OCR engine regression."""

    png = render_visual_png(visual, scale=scale)
    with Image.open(BytesIO(png)) as image:
        out = BytesIO()
        image.convert("RGB").save(out, format="PDF", resolution=144)
        return out.getvalue()


def _render_pdf_text_layout_png(visual: dict[str, Any], *, scale: float) -> bytes:
    page = visual["pages"][0]
    width = max(1, int(page["width_pt"] * scale))
    height = max(1, int(page["height_pt"] * scale))
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    for line in page["lines"]:
        left, bottom, _right, top = line["bbox"]
        font_size = max(8, int(line.get("font_size_pt", 9) * scale))
        font = _font(font_size)
        x = int(left * scale)
        y = int((page["height_pt"] - top) * scale)
        draw.text((x, y), line["text"], fill=(20, 20, 20), font=font)

    return _png_bytes(image)


def _render_image_text_layout_png(visual: dict[str, Any]) -> bytes:
    image = Image.new("RGB", (visual["width_px"], visual["height_px"]), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, visual["width_px"] - 1, visual["height_px"] - 1), outline=(220, 220, 220))

    for line in visual["lines"]:
        left, top, _right, _bottom = line["bbox"]
        font = _font(int(line.get("font_size_px", 16)))
        draw.text((left, top), line["text"], fill=(20, 20, 20), font=font)

    return _png_bytes(image)


def _render_semantic_text_png(text: str) -> bytes:
    lines = [line for line in text.splitlines() if line.strip()]
    font = _font(18)
    image = Image.new("RGB", (1200, max(400, 36 + len(lines) * 28)), "white")
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(lines):
        draw.text((32, 24 + index * 28), line, fill=(20, 20, 20), font=font)
    return _png_bytes(image)


def _png_bytes(image: Image.Image) -> bytes:
    out = BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def _font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    for path in _font_candidates():
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _font_candidates() -> list[Path]:
    return [
        Path("/System/Library/Fonts/Hiragino Sans GB.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/Supplemental/Songti.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
    ]
