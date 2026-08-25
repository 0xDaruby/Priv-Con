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

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")


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
) -> Path:
    """Persist an upload stream under a generated, sanitized temp name."""
    target_path = upload_target_path(upload_dir, job_id, original_filename)

    try:
        with target_path.open("wb") as target:
            shutil.copyfileobj(source, target)
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
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
        except OSError:
            pass
