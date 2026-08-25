"""Tests for immediate, delayed, and orphan cleanup behavior."""

import os
import time
from pathlib import Path

from app.config import settings
from app.services.cleanup_service import (
    cleanup_after_response,
    cleanup_now,
    mark_active_paths,
    sweep_stale_temp_files,
)


def _configure_temp_roots(tmp_path: Path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    output_dir = tmp_path / "outputs"
    upload_dir.mkdir()
    output_dir.mkdir()
    monkeypatch.setattr(settings, "upload_temp_dir", upload_dir)
    monkeypatch.setattr(settings, "output_temp_dir", output_dir)
    monkeypatch.setattr(settings, "cleanup_delay_minutes", 1)
    return upload_dir, output_dir


def test_immediate_cleanup_removes_files_and_directories(
    tmp_path: Path,
    monkeypatch,
) -> None:
    upload_dir, output_dir = _configure_temp_roots(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "cleanup_mode", "immediate")
    upload_path = upload_dir / "upload.pdf"
    output_job_dir = output_dir / "job"
    upload_path.write_bytes(b"input")
    output_job_dir.mkdir()
    (output_job_dir / "result.pdf").write_bytes(b"output")
    mark_active_paths([upload_path, output_job_dir])

    cleanup_after_response([upload_path, output_job_dir])

    assert not upload_path.exists()
    assert not output_job_dir.exists()


def test_delayed_cleanup_waits_until_expiry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    upload_dir, output_dir = _configure_temp_roots(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "cleanup_mode", "delayed")
    upload_path = upload_dir / "upload.pdf"
    output_job_dir = output_dir / "job"
    upload_path.write_bytes(b"input")
    output_job_dir.mkdir()
    (output_job_dir / "result.pdf").write_bytes(b"output")
    mark_active_paths([upload_path, output_job_dir])

    cleanup_after_response([upload_path, output_job_dir])
    completed_at = upload_path.stat().st_mtime

    assert sweep_stale_temp_files(now=completed_at + 59) == 0
    assert upload_path.exists()
    assert output_job_dir.exists()

    assert sweep_stale_temp_files(now=completed_at + 61) == 2
    assert not upload_path.exists()
    assert not output_job_dir.exists()


def test_sweeper_preserves_active_jobs_and_removes_crash_orphans(
    tmp_path: Path,
    monkeypatch,
) -> None:
    upload_dir, _ = _configure_temp_roots(tmp_path, monkeypatch)
    active_path = upload_dir / "active.pdf"
    orphan_path = upload_dir / "orphan.pdf"
    active_path.write_bytes(b"active")
    orphan_path.write_bytes(b"orphan")
    old_time = time.time() - 120
    os.utime(active_path, (old_time, old_time))
    os.utime(orphan_path, (old_time, old_time))
    mark_active_paths([active_path])

    assert sweep_stale_temp_files(now=time.time()) == 1
    assert active_path.exists()
    assert not orphan_path.exists()

    cleanup_now([active_path])
    assert not active_path.exists()
