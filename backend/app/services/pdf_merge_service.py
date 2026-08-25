"""PDF merge service backed by pypdf."""

import logging
import shutil
from pathlib import Path
from typing import Sequence

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from app.config import settings
from app.core.exceptions import PrivConError
from app.core.file_utils import new_job_id, output_dir_for_job


logger = logging.getLogger(__name__)


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
    job_output_dir.mkdir(parents=True, exist_ok=True)
    output_path = job_output_dir / "merged.pdf"

    writer = PdfWriter()
    opened_readers: list[PdfReader] = []

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

                for page in reader.pages:
                    writer.add_page(page)
            except PdfReadError as exc:
                logger.warning("Unreadable PDF encountered for job %s", job_id)
                raise MergeError(
                    code="conversion_failed",
                    message=(
                        "One of the uploaded files is not a valid or readable PDF."
                    ),
                ) from exc

        with output_path.open("wb") as output_file:
            writer.write(output_file)

        logger.info("Job %s merged %s PDF files", job_id, len(input_paths))
        return output_path
    except MergeError:
        _cleanup_dir(job_output_dir)
        raise
    except Exception as exc:
        logger.exception("Unexpected PDF merge failure for job %s", job_id)
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
    shutil.rmtree(path, ignore_errors=True)
