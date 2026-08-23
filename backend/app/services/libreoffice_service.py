"""
LibreOffice headless conversion service.

Design decisions (see libreoffice-service-notes.md, Phase 1 step 3):
  - spawn a fresh LibreOffice process per conversion rather than a
    long-running listener: simpler, better job isolation, easier timeout
    handling, no profile-lock contention between overlapping jobs
  - each job gets its own output dir, its own throwaway LO user profile,
    and a hard subprocess timeout
  - cleanup of the job's own temp artifacts is guaranteed on every path

IMPORTANT: this service does NOT validate that the input is a genuine
Office file. Testing showed LibreOffice will "succeed" (exit code 0) on
plain text or random binary renamed to .docx/.pptx/.xlsx, producing a
garbage PDF instead of erroring. Structural validation (core/validators.py)
must run BEFORE calling convert_to_pdf() — this service trusts its input.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

from app.config import settings
from app.core.exceptions import ConversionError
from app.core.file_utils import output_dir_for_job


def convert_to_pdf(input_path: Path, job_id: str) -> Path:
    """Convert input_path (a validated .docx/.pptx/.xlsx file) to PDF.

    Returns the path to the generated PDF.
    Raises ConversionError on missing input, timeout, or subprocess failure.

    Cleanup guarantees:
      - the job's LibreOffice profile dir is removed on every path (success,
        timeout, or failure)
      - the job's output dir is removed on every failure path (timeout,
        non-zero exit, missing output) so no partial/garbage PDF is left
        behind — callers own cleanup of the output dir on the success path
        (it holds the file they need to return to the client)
    """
    if not input_path.exists():
        raise ConversionError(
            code="conversion_failed",
            message="The uploaded file could not be found for conversion.",
        )

    job_output_dir = output_dir_for_job(settings.output_temp_dir, job_id)
    job_output_dir.mkdir(parents=True, exist_ok=True)

    profile_dir = Path(tempfile.mkdtemp(prefix=f"privcon-lo-profile-{job_id}-"))

    try:
        result = subprocess.run(
            [
                settings.libreoffice_path,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(job_output_dir),
                f"-env:UserInstallation=file://{profile_dir}",
                str(input_path),
            ],
            capture_output=True,
            timeout=settings.conversion_timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(job_output_dir, ignore_errors=True)
        raise ConversionError(
            code="conversion_timeout",
            message="Conversion took too long and was cancelled.",
        )
    except OSError:
        # e.g. LIBREOFFICE_PATH is misconfigured or LibreOffice isn't
        # installed — this is a server/environment problem, not bad input.
        shutil.rmtree(job_output_dir, ignore_errors=True)
        raise ConversionError(
            code="backend_unavailable",
            message="The conversion engine is unavailable. Please check "
            "the server configuration.",
        )
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)

    if result.returncode != 0:
        shutil.rmtree(job_output_dir, ignore_errors=True)
        raise ConversionError(
            code="conversion_failed",
            message="The document could not be converted to PDF.",
        )

    output_path = job_output_dir / f"{input_path.stem}.pdf"
    if not output_path.exists():
        shutil.rmtree(job_output_dir, ignore_errors=True)
        raise ConversionError(
            code="conversion_failed",
            message="The document could not be converted to PDF.",
        )

    return output_path
