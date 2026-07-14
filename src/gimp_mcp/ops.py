"""Shared Pillow image operations used by mock + live assist."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


def load_rgb(path: str | Path) -> Image.Image:
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    return im.convert("RGB")


def auto_orient(im: Image.Image) -> Image.Image:
    return ImageOps.exif_transpose(im).convert("RGB")


def resize(im: Image.Image, width: int, height: int) -> Image.Image:
    return im.resize((max(1, int(width)), max(1, int(height))), Image.Resampling.LANCZOS)


def thumbnail(im: Image.Image, max_width: int, max_height: int) -> Image.Image:
    """Fit inside box preserving aspect ratio (no upscale beyond original)."""
    out = im.copy()
    out.thumbnail((max(1, int(max_width)), max(1, int(max_height))), Image.Resampling.LANCZOS)
    return out


def crop(im: Image.Image, x: int, y: int, width: int, height: int) -> Image.Image:
    box = (int(x), int(y), int(x) + max(1, int(width)), int(y) + max(1, int(height)))
    return im.crop(box)


def flip(im: Image.Image, direction: str = "horizontal") -> Image.Image:
    d = (direction or "horizontal").lower()
    if d in ("vertical", "v"):
        return ImageOps.flip(im)
    return ImageOps.mirror(im)


def rotate(im: Image.Image, degrees: float = 90) -> Image.Image:
    return im.rotate(-float(degrees), expand=True, fillcolor="#000000")


def blur(im: Image.Image, radius: float = 2.0) -> Image.Image:
    return im.filter(ImageFilter.GaussianBlur(radius=max(0.0, float(radius))))


def sharpen(im: Image.Image, percent: float = 150.0, radius: float = 2.0) -> Image.Image:
    # UnsharpMask: percent is strength, radius is blur radius of mask
    return im.filter(
        ImageFilter.UnsharpMask(radius=max(0.1, float(radius)), percent=int(max(1, percent)), threshold=3)
    )


def desaturate(im: Image.Image) -> Image.Image:
    return ImageOps.grayscale(im).convert("RGB")


def invert(im: Image.Image) -> Image.Image:
    return ImageOps.invert(im.convert("RGB"))


def brightness(im: Image.Image, factor: float = 1.2) -> Image.Image:
    return ImageEnhance.Brightness(im).enhance(float(factor))


def contrast(im: Image.Image, factor: float = 1.2) -> Image.Image:
    return ImageEnhance.Contrast(im).enhance(float(factor))


def _font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    size = max(8, int(size))
    candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for path in candidates:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def text_overlay(
    im: Image.Image,
    text: str,
    x: int = 10,
    y: int = 10,
    size: int = 32,
    color: str = "#000000",
) -> Image.Image:
    out = im.copy()
    draw = ImageDraw.Draw(out)
    font = _font(size)
    draw.text((int(x), int(y)), str(text), fill=color, font=font)
    return out


def export(im: Image.Image, path: str | Path, format: str | None = None) -> dict[str, Any]:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fmt = (format or out.suffix.lstrip(".") or "png").upper()
    if fmt == "JPG":
        fmt = "JPEG"
    save_kwargs: dict[str, Any] = {}
    if fmt == "JPEG":
        save_kwargs["quality"] = 92
        save_kwargs["optimize"] = True
    im.save(out, format=fmt, **save_kwargs)
    return {"path": str(out), "format": fmt}


# Pipeline step names → callable
PIPELINE_OPS = {
    "auto_orient": lambda im, **kw: auto_orient(im),
    "resize": lambda im, **kw: resize(im, int(kw["width"]), int(kw["height"])),
    "thumbnail": lambda im, **kw: thumbnail(
        im, int(kw.get("max_width") or kw.get("width", 512)), int(kw.get("max_height") or kw.get("height", 512))
    ),
    "crop": lambda im, **kw: crop(im, int(kw["x"]), int(kw["y"]), int(kw["width"]), int(kw["height"])),
    "flip": lambda im, **kw: flip(im, str(kw.get("direction", "horizontal"))),
    "rotate": lambda im, **kw: rotate(im, float(kw.get("degrees", 90))),
    "blur": lambda im, **kw: blur(im, float(kw.get("radius", 2.0))),
    "sharpen": lambda im, **kw: sharpen(im, float(kw.get("percent", 150)), float(kw.get("radius", 2.0))),
    "desaturate": lambda im, **kw: desaturate(im),
    "invert": lambda im, **kw: invert(im),
    "brightness": lambda im, **kw: brightness(im, float(kw.get("factor", 1.2))),
    "contrast": lambda im, **kw: contrast(im, float(kw.get("factor", 1.2))),
    "text": lambda im, **kw: text_overlay(
        im,
        str(kw.get("text", "")),
        int(kw.get("x", 10)),
        int(kw.get("y", 10)),
        int(kw.get("size", 32)),
        str(kw.get("color", "#ffffff")),
    ),
}


def apply_pipeline(im: Image.Image, steps: list[dict[str, Any]]) -> tuple[Image.Image, list[str]]:
    applied: list[str] = []
    cur = im
    for step in steps:
        op = str(step.get("op") or step.get("name") or "").lower().strip()
        if op not in PIPELINE_OPS:
            raise ValueError(f"unknown pipeline op: {op}")
        params = {k: v for k, v in step.items() if k not in ("op", "name")}
        cur = PIPELINE_OPS[op](cur, **params)
        applied.append(op)
    return cur, applied
