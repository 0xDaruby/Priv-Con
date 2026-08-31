"""Centralized lifecycle management for PrivCon temporary files."""

import asyncio
import os
import threading
import time
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.config import settings
from app.core.file_utils import cleanup_paths

_active_paths: set[Path] = set()
_active_paths_lock = threading.RLock()


def mark_active_paths(paths: Iterable[Path]) -> None:
    """Protect in-flight job paths from the orphan sweeper."""
    with _active_paths_lock:
        _active_paths.update(_path_key(path) for path in paths)


def cleanup_now(paths: Iterable[Path]) -> None:
    """Immediately remove paths and release any active-job protection."""
    cleanup_targets = [Path(path) for path in paths]
    controlled_targets = [
        path for path in cleanup_targets if _is_controlled_cleanup_target(path)
    ]

    try:
        cleanup_paths(controlled_targets)
    finally:
        _release_paths(cleanup_targets)


def cleanup_after_response(paths: Iterable[Path]) -> None:
    """Apply the configured cleanup mode after a response finishes streaming."""
    cleanup_targets = [Path(path) for path in paths]

    if settings.cleanup_mode == "immediate":
        cleanup_now(cleanup_targets)
        return

    # Delayed retention starts when the response completes, not when the
    # upload began. The periodic sweeper removes these paths after expiry.
    completion_time = time.time()

    for path in cleanup_targets:
        if not _is_controlled_cleanup_target(path):
            continue

        try:
            if path.is_symlink():
                os.utime(
                    path,
                    (completion_time, completion_time),
                    follow_symlinks=False,
                )
            elif path.exists():
                os.utime(path, (completion_time, completion_time))
        except (NotImplementedError, OSError):
            pass

    _release_paths(cleanup_targets)


def sweep_stale_temp_files(*, now: float | None = None) -> int:
    """Remove expired top-level artifacts from controlled temp roots."""
    current_time = time.time() if now is None else now
    delay_seconds = max(1, settings.cleanup_delay_minutes * 60)
    cutoff = current_time - delay_seconds
    removed_count = 0

    for root in _controlled_temp_roots():
        try:
            root.mkdir(parents=True, exist_ok=True)
            candidates = list(root.iterdir())
        except OSError:
            continue

        for candidate in candidates:
            if _is_active(candidate):
                continue

            try:
                modified_at = candidate.lstat().st_mtime
            except OSError:
                continue

            if modified_at > cutoff:
                continue

            if not _is_controlled_cleanup_target(candidate):
                continue

            cleanup_paths([candidate])

            if not candidate.exists() and not candidate.is_symlink():
                removed_count += 1

    return removed_count


def purge_orphaned_temp_files_on_startup() -> int:
    """Remove artifacts that cannot belong to the new backend process.

    Job state is intentionally process-local. After a restart there is no
    surviving job record that can claim an upload, LibreOffice profile, or
    result directory left by the previous process, regardless of file age.
    """
    removed_count = 0

    for root in _controlled_temp_roots():
        try:
            root.mkdir(parents=True, exist_ok=True)
            candidates = list(root.iterdir())
        except OSError:
            continue

        for candidate in candidates:
            if _is_active(candidate):
                continue

            if not _is_controlled_cleanup_target(candidate):
                continue

            cleanup_paths([candidate])

            if not candidate.exists() and not candidate.is_symlink():
                removed_count += 1

    return removed_count


async def run_periodic_cleanup(stop_event: asyncio.Event) -> None:
    """Sweep on startup and periodically until application shutdown."""
    interval_seconds = max(
        1,
        min(60, settings.cleanup_delay_minutes * 60),
    )

    while not stop_event.is_set():
        sweep_stale_temp_files()

        # Import lazily to avoid a module cycle: job_service relies on the
        # cleanup primitives above, while the periodic sweep also expires
        # completed in-memory job records and unclaimed result files.
        from app.services.job_service import job_manager

        job_manager.sweep_expired_jobs()

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except TimeoutError:
            continue


@asynccontextmanager
async def cleanup_lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Run the orphan sweeper for the lifetime of the FastAPI application."""
    purge_orphaned_temp_files_on_startup()
    stop_event = asyncio.Event()
    cleanup_task = asyncio.create_task(run_periodic_cleanup(stop_event))

    try:
        yield
    finally:
        stop_event.set()
        await cleanup_task


def _release_paths(paths: Iterable[Path]) -> None:
    with _active_paths_lock:
        for path in paths:
            _active_paths.discard(_path_key(path))


def _is_active(path: Path) -> bool:
    with _active_paths_lock:
        return _path_key(path) in _active_paths


def _path_key(path: Path) -> Path:
    return Path(path).resolve(strict=False)


def _is_controlled_cleanup_target(path: Path) -> bool:
    """Only allow deletion below one of PrivCon's configured temp roots."""
    path = Path(path)

    try:
        roots = _controlled_temp_roots()

        if path.is_symlink():
            candidate = path.parent.resolve(strict=False) / path.name
        else:
            candidate = path.resolve(strict=False)

        return any(candidate != root and root in candidate.parents for root in roots)
    except OSError:
        return False


def _controlled_temp_roots() -> set[Path]:
    """Resolve temp roots while refusing broad or symlinked locations."""
    configured_roots = {
        Path(settings.upload_temp_dir),
        Path(settings.output_temp_dir),
    }
    resolved_roots: set[Path] = set()
    protected_roots = {
        Path.cwd().resolve(strict=False),
        Path.home().resolve(strict=False),
    }

    for configured_root in configured_roots:
        absolute_root = configured_root.absolute()
        resolved_root = configured_root.resolve(strict=False)

        if resolved_root.parent == resolved_root:
            return set()

        if resolved_root in protected_roots:
            return set()

        # A symlinked temp root could be swapped to expose unrelated data to
        # the stale-file sweeper. Refuse it instead of following it.
        if absolute_root != resolved_root:
            return set()

        resolved_roots.add(resolved_root)

    if len(resolved_roots) != 2:
        return set()

    first, second = tuple(resolved_roots)

    if first in second.parents or second in first.parents:
        return set()

    return resolved_roots
