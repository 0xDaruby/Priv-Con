"""Filename sanitization and unique id/path generation for temp storage.

Per PRD 21.3: use generated unique filenames for temp storage, preserve
original filenames only for user-facing download names, sanitize all
user-supplied names.
"""

import re
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO, Iterable

from app.core.exceptions import ValidationError

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")
_UPLOAD_CHUNK_SIZE = 1024 * 1024


def new_job_id() -> str:
    return uuid.uuid4().hex


def sanitize_filename(filename: str) -> str:
    """Strip any directory component and replace anything that isn't
    alphanumeric/._- with an underscore."""
    name = Path(filename or "upload").name  # drops path traversal attempts
    name = _UNSAFE_CHARS.sub("_", name)
    return name or "upload"


def upload_target_path(upload_dir: Path, job_id: str, original_filename: str) -> Path:
    """Unique, sanitized path for a job's uploaded input file.

    The original extension is preserved (LibreOffice's --convert-to filter
    detection relies on it); the job id prefix guarantees concurrent jobs
    never collide.
    """
    safe_name = sanitize_filename(original_filename)
    return upload_dir / f"{job_id}_{safe_name}"


def output_dir_for_job(output_root: Path, job_id: str) -> Path:
    return output_root / job_id


def save_upload_to_temp(
    source: BinaryIO,
    upload_dir: Path,
    job_id: str,
    original_filename: str,
    max_size_bytes: int,
) -> Path:
    """Persist an upload stream while enforcing its configured size limit."""
    if max_size_bytes <= 0:
        raise ValueError("max_size_bytes must be greater than zero")

    target_path = upload_target_path(upload_dir, job_id, original_filename)
    total_bytes = 0

    try:
        with target_path.open("wb") as target:
            while chunk := source.read(_UPLOAD_CHUNK_SIZE):
                total_bytes += len(chunk)

                if total_bytes > max_size_bytes:
                    limit_mb = max_size_bytes // (1024 * 1024)
                    raise ValidationError(
                        code="oversized_file",
                        message=(
                            f"Files larger than {limit_mb} MB are not accepted."
                        ),
                    )

                target.write(chunk)
    except Exception:
        try:
            target_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    return target_path


def cleanup_paths(paths: Iterable[Path]) -> None:
    """Remove temporary files or directories without masking response errors."""
    for path in paths:
        path = Path(path)

        try:
            if path.is_symlink():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
        except OSError:
            pass
