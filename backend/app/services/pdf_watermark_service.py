"""Local vector/image watermarks preserving the original PDF geometry and content."""

import time
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, StreamObject

from app.config import settings
from app.core.exceptions import ConversionError, PrivConError, ValidationError
from app.core.file_utils import (
    enforce_output_size,
    ensure_private_directory,
    new_job_id,
    output_dir_for_job,
    private_binary_writer,
)
from app.core.progress import (
    CancellationCheck,
    JobCancelled,
    ProgressCallback,
    StageCallback,
)
from app.core.validators import validate_pdf_structure
from app.services.cleanup_service import cleanup_now, mark_active_paths
from app.services.pdf_overlay_geometry import (
    displayed_geometry,
    image_mark,
    placed_transform,
    text_mark,
    validate_watermark_image,
)
from app.services.pdf_overlay_options import WatermarkOptions
from app.services.pdf_rotate_service import _reject_signatures
from app.services.pdf_tool_options import selected_page_indices


def _preflight_contents(
    reader: PdfReader, indices: tuple[int, ...], check: Callable[[], None]
) -> None:
    """Bound cumulative decompression before cloning/merging selected content."""
    limit = min(64 * 1024 * 1024, settings.max_output_size_mb * 1024 * 1024)
    total = 0
    for index in indices:
        check()
        contents = reader.pages[index].get("/Contents")
        if contents is None:
            continue
        contents = contents.get_object()
        streams = contents if isinstance(contents, ArrayObject) else [contents]
        if len(streams) > 10000:
            raise ValidationError(
                "output_too_large", "The PDF page contains too many content streams."
            )
        for reference in streams:
            check()
            stream = reference.get_object()
            if not isinstance(stream, StreamObject):
                raise ValidationError(
                    "corrupted_file", "The PDF contains an invalid page content stream."
                )
            total += len(stream.get_data())
            if total > limit:
                raise ValidationError(
                    "output_too_large",
                    "The selected PDF content exceeds the safe overlay processing budget.",
                )


class _BoundedWriter:
    def __init__(self, stream: BinaryIO, check: Callable[[], None]) -> None:
        self.stream = stream
        self.check = check

    def write(self, data: bytes) -> int:
        self.check()
        if self.stream.tell() + len(data) > settings.max_output_size_mb * 1024 * 1024:
            raise ValidationError(
                "output_too_large",
                "The generated PDF exceeds the configured output limit.",
            )
        return self.stream.write(data)

    def tell(self) -> int:
        return self.stream.tell()

    def flush(self) -> None:
        self.stream.flush()


def apply_overlays(
    input_path: Path,
    pages: str | None,
    create_mark: Callable[[int], tuple[bytes, float, float]],
    *,
    position: str,
    margin: float,
    angle: float = 0,
    fraction: float | None = None,
    output_name: str,
    progress_callback: ProgressCallback | None = None,
    finalizing_callback: StageCallback | None = None,
    cancellation_check: CancellationCheck | None = None,
    _deadline: float | None = None,
) -> Path:
    """Shared write/verification lifecycle; each mark is a self-contained local PDF."""
    output_dir = output_dir_for_job(settings.output_temp_dir, new_job_id())
    ensure_private_directory(output_dir)
    mark_active_paths([output_dir])
    output = output_dir / output_name
    deadline = (
        _deadline
        if _deadline is not None
        else time.monotonic() + settings.conversion_timeout_seconds
    )
    reader = writer = None
    mark_readers: dict[bytes, PdfReader] = {}
    mark_bytes = 0

    def check() -> None:
        if cancellation_check:
            cancellation_check()
        if time.monotonic() >= deadline:
            raise ConversionError(
                "conversion_timeout",
                "The PDF overlay exceeded the local processing time limit.",
            )

    try:
        check()
        validate_pdf_structure(input_path)
        reader = PdfReader(str(input_path), strict=True)
        try:
            _reject_signatures(reader)
        except ValidationError as exc:
            if exc.code == "signed_pdf_not_supported":
                raise ValidationError(
                    exc.code,
                    "Signed PDFs cannot be modified because this would invalidate their signatures.",
                ) from exc
            raise
        indices = selected_page_indices(pages, len(reader.pages))
        for page in reader.pages:
            check()
            displayed_geometry(page)
        _preflight_contents(reader, indices, check)
        writer = PdfWriter(clone_from=reader)
        for completed, index in enumerate(indices, 1):
            check()
            page = writer.pages[index]
            page_width, page_height, inverse = displayed_geometry(page)
            mark_data, mark_width, mark_height = create_mark(completed - 1)
            check()
            if mark_data not in mark_readers:
                mark_bytes += len(mark_data)
                if mark_bytes > settings.max_output_size_mb * 1024 * 1024:
                    raise ValidationError(
                        "output_too_large",
                        "The overlay resources exceed the output budget.",
                    )
                mark_readers[mark_data] = PdfReader(BytesIO(mark_data), strict=True)
            placement = placed_transform(
                mark_width,
                mark_height,
                page_width,
                page_height,
                position=position,
                margin=margin,
                angle=angle,
                fraction=fraction,
            )
            # Reuse the same reader/resource identities so image data is imported
            # once rather than duplicated once per selected source page.
            mark = mark_readers[mark_data]
            page.merge_transformed_page(
                mark.pages[0], placement.transform(inverse), over=True, expand=False
            )
            if progress_callback:
                progress_callback(completed, len(indices))
        if finalizing_callback:
            finalizing_callback()
        check()
        with private_binary_writer(output) as stream:
            writer.write(_BoundedWriter(stream, check))
        enforce_output_size(output)
        check()
        validate_pdf_structure(output)
        with PdfReader(str(output), strict=True) as result:
            if len(result.pages) != len(reader.pages) or any(
                a.mediabox != b.mediabox
                or a.cropbox != b.cropbox
                or a.rotation != b.rotation
                for a, b in zip(reader.pages, result.pages)
            ):
                raise ConversionError(
                    "conversion_failed",
                    "The generated PDF geometry could not be verified.",
                )
        check()
        return output
    except (PrivConError, JobCancelled):
        cleanup_now([output_dir])
        raise
    except Exception as exc:
        cleanup_now([output_dir])
        raise ConversionError(
            "conversion_failed", "The PDF overlay could not be generated."
        ) from exc
    finally:
        if writer:
            writer.close()
        if reader:
            reader.close()
        for mark_reader in mark_readers.values():
            mark_reader.close()


def watermark_pdf(
    input_path: Path,
    options: WatermarkOptions,
    image_path: Path | None = None,
    **callbacks,
) -> Path:
    """Add a bounded text or transparent image overlay to selected pages."""
    deadline = time.monotonic() + settings.conversion_timeout_seconds

    def check_validation() -> None:
        cancellation_check = callbacks.get("cancellation_check")
        if cancellation_check:
            cancellation_check()
        if time.monotonic() >= deadline:
            raise ConversionError(
                "conversion_timeout",
                "The PDF overlay exceeded the local processing time limit.",
            )

    check_validation()
    if options.kind == "image":
        if image_path is None:
            raise ValidationError(
                "invalid_overlay_options", "Choose one watermark image."
            )
        validate_watermark_image(image_path, image_path.name)
    elif image_path is not None:
        raise ValidationError(
            "invalid_overlay_options", "Text watermarks do not accept an image."
        )
    check_validation()
    mark: tuple[bytes, float, float] | None = None

    def create_mark(_: int) -> tuple[bytes, float, float]:
        nonlocal mark
        if mark is None:
            mark = (
                image_mark(image_path, options.opacity)
                if image_path is not None
                else text_mark(options.text or "", 100, options.opacity)
            )
        return mark

    return apply_overlays(
        input_path,
        options.pages,
        create_mark,
        position=options.position,
        margin=options.margin,
        angle=options.angle,
        fraction=options.scale,
        output_name="watermarked.pdf",
        _deadline=deadline,
        **callbacks,
    )
