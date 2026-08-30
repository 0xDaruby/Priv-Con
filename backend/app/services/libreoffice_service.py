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

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from app.config import settings
from app.core.exceptions import ConversionError, ValidationError
from app.core.file_utils import (
    enforce_output_size,
    ensure_private_directory,
    output_dir_for_job,
)
from app.core.progress import CancellationCheck, JobCancelled
from app.services.cleanup_service import cleanup_now, mark_active_paths


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
    cleanup_now([output_dir])


def _stop_process(process: subprocess.Popen[str]) -> None:
    """Stop a cancellable LibreOffice child without leaving it running."""
    if process.poll() is not None:
        return

    process.terminate()

    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def _run_cancellable(
    command: list[str],
    *,
    cwd: str,
    environment: dict[str, str],
    creation_flags: int,
    cancellation_check: CancellationCheck,
) -> subprocess.CompletedProcess[str]:
    """Run LibreOffice while periodically observing a cancellation event."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        shell=False,
        cwd=cwd,
        env=environment,
        creationflags=creation_flags,
    )
    deadline = time.monotonic() + settings.conversion_timeout_seconds

    try:
        while True:
            cancellation_check()
            remaining_seconds = deadline - time.monotonic()

            if remaining_seconds <= 0:
                raise subprocess.TimeoutExpired(
                    command,
                    settings.conversion_timeout_seconds,
                )

            try:
                stdout, stderr = process.communicate(
                    timeout=min(0.2, remaining_seconds),
                )
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=process.returncode,
                    stdout=stdout,
                    stderr=stderr,
                )
            except subprocess.TimeoutExpired:
                continue
    except (JobCancelled, subprocess.TimeoutExpired):
        _stop_process(process)
        raise
    except Exception:
        _stop_process(process)
        raise


def convert_to_pdf(
    input_path: Path,
    job_id: str,
    *,
    cancellation_check: CancellationCheck | None = None,
) -> Path:
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

    ensure_private_directory(job_output_dir)
    mark_active_paths([job_output_dir])

    output_path = job_output_dir / f"{input_path.stem}.pdf"

    # Prevent an old file from being mistaken for a new conversion.
    if output_path.exists():
        output_path.unlink()

    # Keep the profile directly below the output root. This stays within the
    # orphan sweeper's allowlist without creating Windows paths long enough to
    # crash LibreOffice when it builds its nested profile directories.
    profile_dir = Path(
        tempfile.mkdtemp(prefix="pc-lo-", dir=settings.output_temp_dir)
    ).resolve()
    mark_active_paths([profile_dir])

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
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    try:
        try:
            if cancellation_check is None:
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
            else:
                result = _run_cancellable(
                    command,
                    cwd=str(Path(libreoffice_executable).parent),
                    environment=process_environment,
                    creation_flags=creation_flags,
                    cancellation_check=cancellation_check,
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

        except JobCancelled:
            _remove_failed_output(job_output_dir)
            raise

        if result.returncode != 0:
            _remove_failed_output(job_output_dir)

            raise ConversionError(
                code="conversion_failed",
                message="The document could not be converted to PDF.",
            )

        if not output_path.is_file():
            _remove_failed_output(job_output_dir)

            raise ConversionError(
                code="conversion_failed",
                message="The document could not be converted to PDF.",
            )

        # Confirm the generated file is actually a PDF.
        try:
            with output_path.open("rb") as generated_pdf:
                has_pdf_signature = generated_pdf.read(5) == b"%PDF-"

        except OSError as exc:
            _remove_failed_output(job_output_dir)

            raise ConversionError(
                code="conversion_failed",
                message="The generated PDF could not be read.",
            ) from exc

        if not has_pdf_signature:
            _remove_failed_output(job_output_dir)

            raise ConversionError(
                code="conversion_failed",
                message="The document could not be converted to PDF.",
            )

        try:
            output_path.chmod(0o600)
        except OSError as exc:
            _remove_failed_output(job_output_dir)
            raise ConversionError(
                code="conversion_failed",
                message="The generated PDF could not be secured.",
            ) from exc

        try:
            enforce_output_size(output_path)
        except ValidationError as exc:
            _remove_failed_output(job_output_dir)
            raise ConversionError(code=exc.code, message=exc.message) from exc

        return output_path

    finally:
        # Always remove the temporary LibreOffice profile.
        cleanup_now([profile_dir])
