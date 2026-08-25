"""PDF merge service backed by pypdf."""

from collections.abc import Sequence
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from app.config import settings
from app.core.exceptions import PrivConError, ValidationError
from app.core.file_utils import (
    enforce_output_size,
    ensure_private_directory,
    new_job_id,
    output_dir_for_job,
    private_binary_writer,
)
from app.services.cleanup_service import cleanup_now, mark_active_paths


class MergeError(PrivConError):
    """Raised when validated PDF inputs cannot be merged."""


def merge_pdfs(input_paths: Sequence[Path]) -> Path:
    """Merge PDFs in order and return a temporary output path.

    The caller owns cleanup of the returned output directory after the
    response has finished streaming. This service cleans its output on every
    failure path.
    """
    if len(input_paths) < 2:
        raise MergeError(
            code="invalid_input",
            message="At least two PDF files are required to merge.",
        )

    job_id = new_job_id()
    job_output_dir = output_dir_for_job(settings.output_temp_dir, job_id)
    ensure_private_directory(job_output_dir)
    mark_active_paths([job_output_dir])
    output_path = job_output_dir / "merged.pdf"

    writer = PdfWriter()
    opened_readers: list[PdfReader] = []
    total_pages = 0

    try:
        for path in input_paths:
            if not path.is_file():
                raise MergeError(
                    code="conversion_failed",
                    message="An uploaded PDF could not be found for merging.",
                )

            try:
                reader = PdfReader(str(path), strict=True)
                opened_readers.append(reader)

                if reader.is_encrypted:
                    raise MergeError(
                        code="password_protected",
                        message="Password-protected PDFs cannot be merged.",
                    )

                if len(reader.pages) == 0:
                    raise MergeError(
                        code="empty_pdf",
                        message="PDF files must contain at least one page.",
                    )

                total_pages += len(reader.pages)

                if total_pages > settings.max_pdf_pages_per_job:
                    raise MergeError(
                        code="too_many_pages",
                        message=(
                            "The combined PDFs exceed the safe page-count limit "
                            f"of {settings.max_pdf_pages_per_job} pages."
                        ),
                    )

                for page in reader.pages:
                    writer.add_page(page)
            except PdfReadError as exc:
                raise MergeError(
                    code="conversion_failed",
                    message=(
                        "One of the uploaded files is not a valid or readable PDF."
                    ),
                ) from exc

        with private_binary_writer(output_path) as output_file:
            writer.write(output_file)

        try:
            enforce_output_size(output_path)
        except ValidationError as exc:
            raise MergeError(code=exc.code, message=exc.message) from exc

        return output_path
    except MergeError:
        _cleanup_dir(job_output_dir)
        raise
    except Exception as exc:
        _cleanup_dir(job_output_dir)
        raise MergeError(
            code="conversion_failed",
            message="Failed to merge PDF files.",
        ) from exc
    finally:
        writer.close()

        for reader in opened_readers:
            reader.close()


def _cleanup_dir(path: Path) -> None:
    cleanup_now([path])
