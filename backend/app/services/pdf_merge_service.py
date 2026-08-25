import logging
import uuid
from pathlib import Path
from typing import List

from pypdf import PdfWriter, PdfReader
from pypdf.errors import PdfReadError

from app.config import settings

logger = logging.getLogger(__name__)


class MergeError(Exception):
    """Base error for merge failures. Carries an error code matching the API error shape."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def merge_pdfs(input_paths: List[Path]) -> Path:
    """
    Merge PDFs in the given order into a single output PDF.

    Each call gets its own job_id and output dir under OUTPUT_TEMP_DIR,
    consistent with the libreoffice_service pattern. Caller is responsible
    for cleanup of input_paths (uploads) and the returned output path
    (via cleanup_service), same as the conversion endpoints.
    """
    if len(input_paths) < 2:
        raise MergeError(
            "invalid_input",
            "At least two PDF files are required to merge."
        )

    job_id = uuid.uuid4().hex
    job_output_dir = Path(settings.OUTPUT_TEMP_DIR) / job_id
    job_output_dir.mkdir(parents=True, exist_ok=True)
    output_path = job_output_dir / "merged.pdf"

    writer = PdfWriter()
    opened_readers = []

    try:
        for path in input_paths:
            if not path.exists():
                raise MergeError(
                    "conversion_failed",
                    f"Input file not found: {path.name}"
                )
            try:
                reader = PdfReader(str(path))
                if reader.is_encrypted:
                    raise MergeError(
                        "conversion_failed",
                        f"'{path.name}' is password-protected and cannot be merged."
                    )
                if len(reader.pages) == 0:
                    raise MergeError(
                        "conversion_failed",
                        f"'{path.name}' has no pages."
                    )
                opened_readers.append(reader)
                for page in reader.pages:
                    writer.add_page(page)
            except PdfReadError as e:
                logger.warning(f"job={job_id} unreadable pdf={path.name} err={e}")
                raise MergeError(
                    "conversion_failed",
                    f"'{path.name}' is not a valid or readable PDF."
                )

        with open(output_path, "wb") as f:
            writer.write(f)

        logger.info(f"job={job_id} merged {len(input_paths)} files -> {output_path.name}")
        return output_path

    except MergeError:
        _cleanup_dir(job_output_dir)
        raise
    except Exception as e:
        logger.error(f"job={job_id} unexpected merge failure: {e}")
        _cleanup_dir(job_output_dir)
        raise MergeError("conversion_failed", "Failed to merge PDF files.")
    finally:
        writer.close()
        for r in opened_readers:
            r.close()


def _cleanup_dir(path: Path):
    try:
        if path.exists():
            for f in path.iterdir():
                f.unlink(missing_ok=True)
            path.rmdir()
    except OSError as e:
        logger.warning(f"cleanup failed for {path}: {e}")