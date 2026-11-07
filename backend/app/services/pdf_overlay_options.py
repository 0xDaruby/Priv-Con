"""Strict immutable multipart option contracts for local PDF overlays."""

import json
import math
from dataclasses import dataclass

from app.config import settings
from app.core.exceptions import ValidationError
from app.services.pdf_tool_options import validate_page_selection

POSITIONS = frozenset(
    {
        "top-left",
        "top-center",
        "top-right",
        "center-left",
        "center",
        "center-right",
        "bottom-left",
        "bottom-center",
        "bottom-right",
    }
)
NUMBER_POSITIONS = frozenset(
    position for position in POSITIONS if not position.startswith("center")
)


def _invalid(message: str) -> ValidationError:
    return ValidationError("invalid_overlay_options", message)


def _number(value: object, low: float, high: float, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not low <= value <= high
        or not math.isfinite(value)
    ):
        raise _invalid(f"{name} must be a finite number from {low:g} to {high:g}.")
    return float(value)


def _choice(value: object, choices: frozenset[str], name: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise _invalid(f"Choose a supported {name}.")
    return value


@dataclass(frozen=True)
class WatermarkOptions:
    pages: str | None = None
    kind: str = "text"
    text: str | None = "CONFIDENTIAL"
    position: str = "center"
    angle: float = 0
    opacity: float = 0.25
    scale: float = 0.5
    margin: float = 18

    def __post_init__(self) -> None:
        object.__setattr__(self, "pages", validate_page_selection(self.pages))
        _choice(self.kind, frozenset({"text", "image"}), "watermark type")
        _choice(self.position, POSITIONS, "watermark position")
        for name, low, high in (
            ("angle", -180, 180),
            ("opacity", 0.1, 1),
            ("scale", 0.1, 1),
            ("margin", 12, 144),
        ):
            object.__setattr__(
                self, name, _number(getattr(self, name), low, high, name)
            )
        if self.kind == "text":
            if (
                not isinstance(self.text, str)
                or not 1 <= len(self.text) <= 120
                or not self.text.strip()
                or any(
                    not (32 <= ord(char) <= 126 or 160 <= ord(char) <= 255)
                    for char in self.text
                )
            ):
                raise _invalid(
                    "Use 1–120 printable English/Western Latin characters supported by Helvetica."
                )
        elif self.text is not None:
            raise _invalid("Image watermarks must omit text.")


@dataclass(frozen=True)
class PageNumberOptions:
    pages: str | None = None
    position: str = "bottom-center"
    margin: float = 18
    font_size: float = 12
    start: int = 1
    format: str = "number"

    def __post_init__(self) -> None:
        object.__setattr__(self, "pages", validate_page_selection(self.pages))
        _choice(self.position, NUMBER_POSITIONS, "page-number position")
        _choice(self.format, frozenset({"number", "page"}), "page-number format")
        object.__setattr__(self, "margin", _number(self.margin, 12, 144, "margin"))
        object.__setattr__(
            self, "font_size", _number(self.font_size, 8, 48, "font size")
        )
        if (
            isinstance(self.start, bool)
            or not isinstance(self.start, int)
            or not 1 <= self.start <= 999999
        ):
            raise _invalid("The starting number must be an integer from 1 to 999999.")


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _invalid("Overlay options cannot contain duplicate keys.")
        result[key] = value
    return result


def overlay_options(
    tool: str, pages: str | None, raw: str | None
) -> WatermarkOptions | PageNumberOptions:
    if raw is not None and len(raw) > settings.max_form_field_size_kb * 1024:
        raise _invalid("The overlay options are too long.")
    try:
        data = json.loads(raw if raw is not None else "{}", object_pairs_hook=_pairs)
    except (ValueError, TypeError, RecursionError) as exc:
        raise _invalid("Overlay options must be a JSON object.") from exc
    if not isinstance(data, dict):
        raise _invalid("Overlay options must be a JSON object.")
    cls = WatermarkOptions if tool == "pdf-watermark" else PageNumberOptions
    allowed = set(cls.__dataclass_fields__) - {"pages"}
    if set(data) - allowed:
        raise _invalid("The overlay options contain unsupported fields.")
    if cls is WatermarkOptions and data.get("kind") == "image":
        if "text" in data:
            raise _invalid("Image watermarks must omit text.")
        data["text"] = None
    return cls(pages=pages, **data)


def validate_overlay_image_choice(
    options: WatermarkOptions | PageNumberOptions, image_count: int
) -> None:
    expected = int(isinstance(options, WatermarkOptions) and options.kind == "image")
    if image_count != expected:
        raise _invalid(
            "Image mode requires exactly one watermark image; other modes accept none."
        )
