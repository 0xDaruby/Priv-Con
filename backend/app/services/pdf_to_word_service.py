"""Orchestrate safe, local PDF-to-Word conversion."""

import zipfile
from collections.abc import Callable
from pathlib import Path

from app.config import settings
from app.core.exceptions import ConversionError, ValidationError
from app.core.file_utils import (
    enforce_output_size,
    ensure_private_directory,
    output_dir_for_job,
)
from app.services.cleanup_service import cleanup_now, mark_active_paths
from app.services.pdf_to_word_engines import (
    EDITABLE_MODE,
    SUPPORTED_PDF_TO_WORD_MODES,
    get_pdf_to_word_engine,
)

CancellationCheck = Callable[[], None]


def validate_pdf_to_word_mode(value: str | None) -> str:
    """Normalize the public conversion mode without guessing invalid values."""
    mode = (value or EDITABLE_MODE).strip().lower()

    if mode not in SUPPORTED_PDF_TO_WORD_MODES:
        raise ValidationError(
            code="invalid_conversion_mode",
            message=(
                "Choose Editable Word or Preserve Appearance for this conversion."
            ),
        )

    return mode


def pdf_to_docx(
    input_path: Path,
    job_id: str,
    *,
    mode: str = EDITABLE_MODE,
    cancellation_check: CancellationCheck | None = None,
) -> Path:
    """Convert a validated PDF using the explicitly selected local engine."""
    input_path = Path(input_path)
    selected_mode = validate_pdf_to_word_mode(mode)

    if not input_path.is_file():
        raise ConversionError(
            code="conversion_failed",
            message="The uploaded PDF could not be found for conversion.",
        )

    job_output_dir = Path(
        output_dir_for_job(settings.output_temp_dir, job_id)
    ).resolve()
    ensure_private_directory(job_output_dir)
    mark_active_paths([job_output_dir])
    output_path = job_output_dir / f"{input_path.stem}.docx"

    try:
        engine = get_pdf_to_word_engine(selected_mode)
        engine.convert(
            input_path,
            output_path,
            cancellation_check=cancellation_check,
        )

        with zipfile.ZipFile(output_path) as archive:
            document_xml = archive.read("word/document.xml")
            if not document_xml or not (
                b"<w:t" in document_xml or b"<w:drawing" in document_xml
            ):
                raise ConversionError(
                    code="conversion_failed",
                    message="The PDF could not be converted to a Word document.",
                )

        output_path.chmod(0o600)

        try:
            enforce_output_size(output_path)
        except ValidationError as exc:
            raise ConversionError(code=exc.code, message=exc.message) from exc

        return output_path
    except ConversionError:
        cleanup_now([job_output_dir])
        raise
    except ValidationError:
        cleanup_now([job_output_dir])
        raise
    except Exception as exc:
        cleanup_now([job_output_dir])
        message = (
            "Editable layout conversion could not safely complete this PDF. "
            "Try Preserve Appearance mode."
            if selected_mode == EDITABLE_MODE
            else "The PDF could not be converted in Preserve Appearance mode."
        )
        raise ConversionError(
            code=(
                "layout_conversion_failed"
                if selected_mode == EDITABLE_MODE
                else "conversion_failed"
            ),
            message=message,
        ) from exc
