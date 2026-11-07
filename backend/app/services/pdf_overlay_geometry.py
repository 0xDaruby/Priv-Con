"""Create bounded local marks and map displayed crop coordinates back to PDF space."""

import math
import warnings
from io import BytesIO
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import Transformation
from pypdf._page import PageObject

from app.config import settings
from app.core.exceptions import ValidationError
from app.core.validators import validate_image_extension, validate_image_structure


def _geometry_error() -> ValidationError:
    return ValidationError(
        "unsupported_pdf_geometry",
        "This PDF has unsupported page geometry. Use finite page boxes, right-angle rotations and UserUnit 1.",
    )


def displayed_geometry(page: PageObject) -> tuple[float, float, Transformation]:
    """Return displayed crop dimensions and its inverse PDF rotation transform."""
    try:
        unit = float(page.get("/UserUnit", 1))
        raw_rotation = float(page.get("/Rotate", 0))
        media = tuple(float(value) for value in page.mediabox)
        crop = tuple(float(value) for value in page.cropbox)
        if (
            unit != 1
            or not math.isfinite(raw_rotation)
            or raw_rotation % 90
            or not all(math.isfinite(value) for value in (*media, *crop))
        ):
            raise _geometry_error()
        mx0, my0, mx1, my1 = media
        x0, y0, x1, y1 = crop
        width, height = x1 - x0, y1 - y0
        if (
            not (mx0 <= x0 < x1 <= mx1 and my0 <= y0 < y1 <= my1)
            or min(width, height) < 1
            or max(width, height) > 14400
        ):
            raise _geometry_error()
        rotation = int(raw_rotation) % 360
        matrix = {
            0: (1, 0, 0, 1, x0, y0),
            90: (0, 1, -1, 0, x1, y0),
            180: (-1, 0, 0, -1, x1, y1),
            270: (0, -1, 1, 0, x0, y1),
        }[rotation]
        if rotation in {90, 270}:
            width, height = height, width
        return width, height, Transformation(matrix)
    except ValidationError:
        raise
    except (ValueError, TypeError, OverflowError) as exc:
        raise _geometry_error() from exc


def validate_watermark_image(path: Path, filename: str) -> None:
    """Check the stricter watermark pixel budget before an image is decoded."""
    validate_image_extension(filename)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path, formats=["PNG", "JPEG", "WEBP"]) as image:
                if image.width * image.height > min(
                    16_000_000, settings.max_image_pixels
                ):
                    raise ValidationError(
                        "oversized_file",
                        "Watermark images must contain at most 16 million pixels and fit the configured image limit.",
                    )
        validate_image_structure(path, filename)
    except ValidationError:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise ValidationError(
            "corrupted_file", "The watermark image is not valid or readable."
        ) from exc


def text_mark(text: str, size: float, opacity: float) -> tuple[bytes, float, float]:
    font = pymupdf.Font("helv")
    if any(not font.has_glyph(ord(char)) for char in text):
        raise ValidationError(
            "invalid_overlay_options",
            "The watermark contains a glyph unsupported by Helvetica.",
        )
    width = font.text_length(text, fontsize=size)
    height = (font.ascender - font.descender) * size
    with pymupdf.open() as document:
        page = document.new_page(width=width + 0.01, height=height + 0.01)
        page.insert_text(
            (0, font.ascender * size),
            text,
            fontsize=size,
            fontname="helv",
            fill_opacity=opacity,
        )
        return document.tobytes(), width + 0.01, height + 0.01


def image_mark(path: Path, opacity: float) -> tuple[bytes, float, float]:
    with Image.open(path, formats=["PNG", "JPEG", "WEBP"]) as source:
        source.seek(0)
        with (
            ImageOps.exif_transpose(source) as oriented,
            oriented.convert("RGBA") as image,
        ):
            alpha = image.getchannel("A")
            try:
                adjusted = alpha.point(lambda value: round(value * opacity))
                try:
                    image.putalpha(adjusted)
                finally:
                    adjusted.close()
            finally:
                alpha.close()
            stream = BytesIO()
            image.save(stream, format="PNG")
            width, height = image.size
    with pymupdf.open() as document:
        page = document.new_page(width=width, height=height)
        page.insert_image(page.rect, stream=stream.getvalue())
        return document.tobytes(), float(width), float(height)


def placed_transform(
    width: float,
    height: float,
    page_width: float,
    page_height: float,
    *,
    position: str,
    margin: float,
    angle: float = 0,
    fraction: float | None = None,
) -> Transformation:
    """Fit a rotated mark to a displayed page; labels retain their exact font size."""
    available_width, available_height = (
        page_width - 2 * margin,
        page_height - 2 * margin,
    )
    radians = math.radians(angle)
    cosine, sine = math.cos(radians), math.sin(radians)
    corners = [
        (x * cosine - y * sine, x * sine + y * cosine)
        for x, y in ((0, 0), (width, 0), (0, height), (width, height))
    ]
    min_x, max_x = min(x for x, _ in corners), max(x for x, _ in corners)
    min_y, max_y = min(y for _, y in corners), max(y for _, y in corners)
    box_width, box_height = max_x - min_x, max_y - min_y
    if available_width <= 0 or available_height <= 0:
        raise ValidationError(
            "invalid_overlay_options", "The margins leave no room on a selected page."
        )
    scale = (
        min(
            available_width * fraction / box_width,
            available_height * fraction / box_height,
        )
        if fraction is not None
        else 1
    )
    box_width, box_height = box_width * scale, box_height * scale
    if box_width > available_width + 0.001 or box_height > available_height + 0.001:
        raise ValidationError(
            "invalid_overlay_options",
            "The page-number label cannot fit inside a selected page's margins. Reduce font size or margins.",
        )
    x = (
        margin
        if position.endswith("left")
        else page_width - margin - box_width
        if position.endswith("right")
        else (page_width - box_width) / 2
    )
    y = (
        page_height - margin - box_height
        if position.startswith("top")
        else margin
        if position.startswith("bottom")
        else (page_height - box_height) / 2
    )
    return (
        Transformation()
        .rotate(angle)
        .scale(scale)
        .translate(x - min_x * scale, y - min_y * scale)
    )
