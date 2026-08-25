"""Filename sanitization and unique id/path generation for temp storage.

Per PRD 21.3: use generated unique filenames for temp storage, preserve
original filenames only for user-facing download names, sanitize all
user-supplied names.
"""

import os
import re
import shutil
import uuid
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from app.config import settings
from app.core.exceptions import ValidationError

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")
_UPLOAD_CHUNK_SIZE = 1024 * 1024


def new_job_id() -> str:
    return uuid.uuid4().hex


def sanitize_filename(filename: str) -> str:
    """Strip any directory component and replace anything that isn't
    alphanumeric/._- with an underscore."""
    # Normalize both POSIX and Windows separators regardless of the host OS.
    name = (filename or "upload").replace("\\", "/").rsplit("/", 1)[-1]
    name = _UNSAFE_CHARS.sub("_", name)
    name = name.strip()

    if name in {"", ".", ".."}:
        name = "upload"

    # Keep generated temp paths and response headers within conservative
    # cross-platform limits while retaining a useful extension.
    if len(name) > 128:
        suffix = Path(name).suffix[:16]
        stem_limit = max(1, 128 - len(suffix))
        name = f"{Path(name).stem[:stem_limit]}{suffix}"

    return name


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


def ensure_private_directory(path: Path) -> None:
    """Create a job directory with owner-only POSIX permissions."""
    path.mkdir(mode=0o700, parents=True, exist_ok=False)


@contextmanager
def private_binary_writer(path: Path) -> Iterator[BinaryIO]:
    """Open a new private binary file without following a pre-existing path."""
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
        0o600,
    )

    with os.fdopen(descriptor, "wb") as output:
        yield output


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
        with private_binary_writer(target_path) as target:
            while chunk := source.read(_UPLOAD_CHUNK_SIZE):
                total_bytes += len(chunk)

                if total_bytes > max_size_bytes:
                    limit_mb = max_size_bytes // (1024 * 1024)
                    raise ValidationError(
                        code="oversized_file",
                        message=(f"Files larger than {limit_mb} MB are not accepted."),
                    )

                target.write(chunk)
    except Exception:
        try:
            target_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    return target_path


def enforce_total_upload_size(total_bytes: int) -> None:
    """Reject a job whose saved inputs exceed the aggregate upload limit."""
    max_total_bytes = settings.max_total_upload_size_mb * 1024 * 1024

    if total_bytes > max_total_bytes:
        raise ValidationError(
            code="oversized_request",
            message=(
                "The combined upload size exceeds the "
                f"{settings.max_total_upload_size_mb} MB request limit."
            ),
        )


def enforce_output_size(output_path: Path) -> None:
    """Reject generated output that exceeds the configured disk bound."""
    max_output_bytes = settings.max_output_size_mb * 1024 * 1024

    try:
        output_size = output_path.stat().st_size
    except OSError as exc:
        raise ValidationError(
            code="file_processing_failed",
            message="The generated output could not be inspected.",
        ) from exc

    if output_size > max_output_bytes:
        raise ValidationError(
            code="output_too_large",
            message=(
                "The generated output exceeds the safe processing limit. "
                "Use fewer or smaller inputs."
            ),
        )


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
