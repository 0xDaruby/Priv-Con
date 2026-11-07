"""Validated immutable options shared by PDF utility routes and jobs."""

import re
from dataclasses import dataclass

from app.config import settings
from app.core.exceptions import ValidationError
from app.services.pdf_split_service import SplitError, parse_page_ranges


def validate_page_selection(pages: str | None) -> str | None:
    """Check syntax before persistence; resolve bounds after reading the PDF."""
    normalized = (pages or "").strip()
    if not normalized:
        return None
    # Bound parsing/allocation even for direct service callers.
    if len(normalized) > settings.max_form_field_size_kb * 1024:
        raise ValidationError("invalid_page_ranges", "The page selection is too long.")
    try:
        parse_page_ranges(normalized, settings.max_pdf_pages_per_job)
    except SplitError as exc:
        raise ValidationError(exc.code, exc.message) from exc
    except ValueError as exc:
        raise ValidationError(
            "invalid_page_ranges", "Page numbers exceed the supported range."
        ) from exc
    return normalized


def selected_page_indices(pages: str | None, page_count: int) -> tuple[int, ...]:
    """Return unique zero-based selected pages in source-document order."""
    if not pages:
        return tuple(range(page_count))
    try:
        ranges = parse_page_ranges(pages, page_count)
    except SplitError as exc:
        raise ValidationError(exc.code, exc.message) from exc
    return tuple(
        sorted(page - 1 for item in ranges for page in range(item.start, item.end + 1))
    )


def _integer(value: str | int, code: str, message: str) -> int:
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]{1,3}", str(value)):
        raise ValidationError(code, message)
    return int(value)


@dataclass(frozen=True)
class RotateOptions:
    pages: str | None = None
    angle: int = 90

    def __post_init__(self) -> None:
        object.__setattr__(self, "pages", validate_page_selection(self.pages))
        angle = _integer(
            self.angle,
            "invalid_rotation",
            "Choose a clockwise rotation of 90, 180 or 270 degrees.",
        )
        if angle not in {90, 180, 270}:
            raise ValidationError(
                "invalid_rotation",
                "Choose a clockwise rotation of 90, 180 or 270 degrees.",
            )
        object.__setattr__(self, "angle", angle)


@dataclass(frozen=True)
class JpegOptions:
    pages: str | None = None
    dpi: int = 144
    quality: int = 85

    def __post_init__(self) -> None:
        object.__setattr__(self, "pages", validate_page_selection(self.pages))
        message = "Use a DPI from 72 to 300 and JPEG quality from 40 to 95."
        dpi = _integer(self.dpi, "invalid_render_options", message)
        quality = _integer(self.quality, "invalid_render_options", message)
        if not 72 <= dpi <= 300 or not 40 <= quality <= 95:
            raise ValidationError("invalid_render_options", message)
        object.__setattr__(self, "dpi", dpi)
        object.__setattr__(self, "quality", quality)


def rotation_options(pages: str | None, angle: str | None) -> RotateOptions:
    value = _integer(
        angle if angle is not None else 90,
        "invalid_rotation",
        "Choose a clockwise rotation of 90, 180 or 270 degrees.",
    )
    return RotateOptions(pages=pages, angle=value)


def jpeg_options(
    pages: str | None, dpi: str | None, quality: str | None
) -> JpegOptions:
    message = "Use a DPI from 72 to 300 and JPEG quality from 40 to 95."
    return JpegOptions(
        pages=pages,
        dpi=_integer(
            dpi if dpi is not None else 144, "invalid_render_options", message
        ),
        quality=_integer(
            quality if quality is not None else 85, "invalid_render_options", message
        ),
    )
