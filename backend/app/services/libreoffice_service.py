"""
LibreOffice headless conversion service.

Design decisions:
  - spawn a fresh LibreOffice process per conversion
  - give every conversion its own output directory
  - give every conversion a unique LibreOffice user profile
  - enforce a hard subprocess timeout
  - clean temporary artifacts on every failure path

IMPORTANT:
This service assumes structural validation has already been performed by
core/validators.py before convert_to_pdf() is called.
"""

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.config import settings
from app.core.exceptions import ConversionError
from app.core.file_utils import output_dir_for_job


logger = logging.getLogger(__name__)


def _resolve_libreoffice_executable() -> str:
    """Resolve LibreOffice from the configured path or system PATH."""
    configured_path = str(settings.libreoffice_path).strip().strip('"')

    if not configured_path:
        raise ConversionError(
            code="backend_unavailable",
            message="The conversion engine is not configured.",
        )

    explicit_path = Path(configured_path).expanduser()

    if explicit_path.is_file():
        return str(explicit_path.resolve())

    discovered_path = shutil.which(configured_path)

    if discovered_path:
        return discovered_path

    raise ConversionError(
        code="backend_unavailable",
        message=(
            "The conversion engine is unavailable. "
            "Please check the server configuration."
        ),
    )


def _remove_failed_output(output_dir: Path) -> None:
    """Remove all output artifacts belonging to a failed job."""
    shutil.rmtree(output_dir, ignore_errors=True)


def convert_to_pdf(input_path: Path, job_id: str) -> Path:
    """Convert a validated DOCX, PPTX, or XLSX file to PDF.

    Returns the path to the generated PDF.

    The caller owns output cleanup after a successful response. This
    function removes the output directory on failure and always removes
    its temporary LibreOffice profile.
    """
    input_path = Path(input_path)

    if not input_path.is_file():
        raise ConversionError(
            code="conversion_failed",
            message="The uploaded file could not be found for conversion.",
        )

    input_path = input_path.resolve()
    libreoffice_executable = _resolve_libreoffice_executable()

    job_output_dir = Path(
        output_dir_for_job(settings.output_temp_dir, job_id)
    ).resolve()

    job_output_dir.mkdir(parents=True, exist_ok=True)

    output_path = job_output_dir / f"{input_path.stem}.pdf"

    # Prevent an old file from being mistaken for a new conversion.
    if output_path.exists():
        output_path.unlink()

    # tempfile.mkdtemp() creates a unique, writable profile for every job.
    profile_dir = Path(
        tempfile.mkdtemp(prefix="privcon-lo-profile-")
    ).resolve()

    # Path.as_uri() correctly produces:
    # Windows: file:///C:/Users/David/...
    # Linux:   file:///tmp/...
    profile_uri = profile_dir.as_uri()

    command = [
        libreoffice_executable,
        f"-env:UserInstallation={profile_uri}",
        "--headless",
        "--nologo",
        "--nodefault",
        "--norestore",
        "--convert-to",
        "pdf",
        "--outdir",
        str(job_output_dir),
        str(input_path),
    ]

    # Avoid external Python variables interfering with LibreOffice's
    # bundled runtime.
    process_environment = os.environ.copy()
    process_environment.pop("PYTHONHOME", None)
    process_environment.pop("PYTHONPATH", None)

    # Prevent soffice.com from creating an extra console window on Windows.
    creation_flags = (
        subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    )

    try:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=settings.conversion_timeout_seconds,
                check=False,
                shell=False,
                cwd=str(Path(libreoffice_executable).parent),
                env=process_environment,
                creationflags=creation_flags,
            )

        except subprocess.TimeoutExpired as exc:
            _remove_failed_output(job_output_dir)

            raise ConversionError(
                code="conversion_timeout",
                message="Conversion took too long and was cancelled.",
            ) from exc

        except OSError as exc:
            _remove_failed_output(job_output_dir)

            raise ConversionError(
                code="backend_unavailable",
                message=(
                    "The conversion engine is unavailable. "
                    "Please check the server configuration."
                ),
            ) from exc

        if result.returncode != 0:
            logger.error(
                "LibreOffice conversion failed for job %s "
                "with return code %s",
                job_id,
                result.returncode,
            )

            _remove_failed_output(job_output_dir)

            raise ConversionError(
                code="conversion_failed",
                message="The document could not be converted to PDF.",
            )

        if not output_path.is_file():
            logger.error(
                "LibreOffice returned success for job %s "
                "without producing a PDF",
                job_id,
            )

            _remove_failed_output(job_output_dir)

            raise ConversionError(
                code="conversion_failed",
                message="The document could not be converted to PDF.",
            )

        # Confirm the generated file is actually a PDF.
        try:
            with output_path.open("rb") as generated_pdf:
                has_pdf_signature = (
                    generated_pdf.read(5) == b"%PDF-"
                )

        except OSError as exc:
            _remove_failed_output(job_output_dir)

            raise ConversionError(
                code="conversion_failed",
                message="The generated PDF could not be read.",
            ) from exc

        if not has_pdf_signature:
            logger.error(
                "LibreOffice produced invalid PDF output for job %s",
                job_id,
            )

            _remove_failed_output(job_output_dir)

            raise ConversionError(
                code="conversion_failed",
                message="The document could not be converted to PDF.",
            )

        return output_path

    finally:
        # Always remove the temporary LibreOffice profile.
        shutil.rmtree(profile_dir, ignore_errors=True)