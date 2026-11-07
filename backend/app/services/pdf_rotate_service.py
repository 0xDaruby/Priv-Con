"""Local page rotation preserving document order and existing page geometry."""

import time
from pathlib import Path

from pypdf import PdfReader, PdfWriter

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
from app.services.cleanup_service import cleanup_now, mark_active_paths
from app.services.pdf_tool_options import RotateOptions, selected_page_indices


def _reject_signatures(reader: PdfReader) -> None:
    """Reject filled signature fields/certification without touching other tools."""
    root = reader.trailer["/Root"]
    if root.get("/Perms"):
        raise ValidationError(
            "signed_pdf_not_supported",
            "Signed PDFs cannot be rotated because this would invalidate their signatures.",
        )
    acroform = root.get("/AcroForm")
    if not acroform:
        return
    stack = [
        (reference, None) for reference in acroform.get_object().get("/Fields", [])
    ]
    seen: set[int] = set()
    while stack:
        reference, inherited_type = stack.pop()
        field = reference.get_object()
        identity = id(field)
        if identity in seen:
            continue
        seen.add(identity)
        field_type = field.get("/FT", inherited_type)
        if field_type == "/Sig" and field.get("/V"):
            raise ValidationError(
                "signed_pdf_not_supported",
                "Signed PDFs cannot be rotated because this would invalidate their signatures.",
            )
        if len(seen) > 10_000:
            raise ValidationError(
                "invalid_input",
                "The PDF contains too many form fields to inspect safely.",
            )
        stack.extend((child, field_type) for child in field.get("/Kids", []))


def rotate_pdf(
    input_path: Path,
    options: RotateOptions,
    *,
    progress_callback: ProgressCallback | None = None,
    finalizing_callback: StageCallback | None = None,
    cancellation_check: CancellationCheck | None = None,
) -> Path:
    """Write a distinct PDF, rotating only selected pages clockwise."""
    output_dir = output_dir_for_job(settings.output_temp_dir, new_job_id())
    ensure_private_directory(output_dir)
    mark_active_paths([output_dir])
    output = output_dir / "rotated.pdf"
    deadline = time.monotonic() + settings.conversion_timeout_seconds
    reader = None
    writer = None

    def check() -> None:
        if cancellation_check:
            cancellation_check()
        if time.monotonic() >= deadline:
            raise ConversionError(
                "conversion_timeout",
                "PDF rotation exceeded the local processing time limit.",
            )

    try:
        check()
        reader = PdfReader(str(input_path), strict=True)
        _reject_signatures(reader)
        indices = selected_page_indices(options.pages, len(reader.pages))
        writer = PdfWriter(clone_from=reader)
        for completed, index in enumerate(indices, 1):
            check()
            writer.pages[index].rotate(options.angle)
            if progress_callback:
                progress_callback(completed, len(indices))
        if finalizing_callback:
            finalizing_callback()
        check()
        with private_binary_writer(output) as stream:
            writer.write(stream)
        enforce_output_size(output)
        with PdfReader(str(output), strict=True) as result:
            if len(result.pages) != len(reader.pages):
                raise ConversionError(
                    "conversion_failed", "The rotated PDF could not be verified."
                )
        check()
        return output
    except (PrivConError, JobCancelled):
        cleanup_now([output_dir])
        raise
    except Exception as exc:
        cleanup_now([output_dir])
        raise ConversionError(
            "conversion_failed", "The PDF could not be rotated."
        ) from exc
    finally:
        if reader:
            reader.close()
        if writer:
            writer.close()
