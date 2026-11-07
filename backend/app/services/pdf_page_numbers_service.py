"""Sequential page labels using the watermark slice's tested vector geometry."""

from pathlib import Path

from app.services.pdf_overlay_geometry import text_mark
from app.services.pdf_overlay_options import PageNumberOptions
from app.services.pdf_watermark_service import apply_overlays


def add_page_numbers(input_path: Path, options: PageNumberOptions, **callbacks) -> Path:
    """Advance once per selected page, in original document order."""

    def create_mark(selected_index: int) -> tuple[bytes, float, float]:
        number = options.start + selected_index
        label = f"Page {number}" if options.format == "page" else str(number)
        return text_mark(label, options.font_size, 1)

    return apply_overlays(
        input_path,
        options.pages,
        create_mark,
        position=options.position,
        margin=options.margin,
        output_name="numbered.pdf",
        **callbacks,
    )
