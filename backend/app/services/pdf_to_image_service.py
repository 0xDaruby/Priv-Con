"""Bounded JPEG export with interruptible ownership of native rendering."""

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.core.exceptions import ConversionError, PrivConError
from app.core.file_utils import (
    enforce_output_size,
    ensure_private_directory,
    new_job_id,
    output_dir_for_job,
    private_binary_writer,
    sanitize_filename,
)
from app.core.progress import (
    CancellationCheck,
    JobCancelled,
    ProgressCallback,
    StageCallback,
)
from app.core.validators import validate_pdf_structure
from app.services.cleanup_service import cleanup_now, mark_active_paths
from app.services.pdf_tool_options import JpegOptions, selected_page_indices


@dataclass(frozen=True)
class JpegResult:
    path: Path
    media_type: str
    download_name: str


def _stop_worker(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


def pdf_to_jpeg(
    input_path: Path,
    original_filename: str,
    options: JpegOptions,
    *,
    progress_callback: ProgressCallback | None = None,
    finalizing_callback: StageCallback | None = None,
    cancellation_check: CancellationCheck | None = None,
) -> JpegResult:
    """Render pages in a subprocess that can be stopped during a native call."""
    page_count = validate_pdf_structure(input_path)
    indices = selected_page_indices(options.pages, page_count)
    stem = Path(sanitize_filename(original_filename)).stem.strip(".") or "document"
    # Leave room for source-page suffix and extension within Windows limits.
    stem = stem[:100]
    output_dir = output_dir_for_job(settings.output_temp_dir, new_job_id())
    ensure_private_directory(output_dir)
    mark_active_paths([output_dir])
    process = None
    deadline = time.monotonic() + settings.conversion_timeout_seconds

    def check() -> None:
        if cancellation_check:
            cancellation_check()
        if time.monotonic() >= deadline:
            raise ConversionError(
                "conversion_timeout",
                "JPEG export exceeded the local processing time limit.",
            )

    try:
        check()
        spec = {
            "input_path": str(input_path.resolve()),
            "output_dir": str(output_dir.resolve()),
            "page_count": page_count,
            "indices": indices,
            "stem": stem,
            "dpi": options.dpi,
            "quality": options.quality,
            "max_page_pixels": settings.max_pdf_render_pixels,
            "max_total_pixels": settings.max_total_pdf_render_pixels,
            "max_bytes": settings.max_output_size_mb * 1024 * 1024,
        }
        # A pipe write can block before deadline polling when a native worker
        # stalls during startup. Deliver bounded metadata in the private job
        # directory so monitoring starts immediately after process creation.
        spec_path = output_dir / "render-spec.json"
        with private_binary_writer(spec_path) as stream:
            stream.write(json.dumps(spec).encode("utf-8"))
        process = subprocess.Popen(
            [sys.executable, "-m", "app.services.pdf_to_image_worker", str(spec_path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            shell=False,
            cwd=str(Path(__file__).resolve().parents[2]),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if os.name == "nt"
            else 0,
        )
        assert process.stdout is not None
        completed = 0
        while process.poll() is None:
            check()
            try:
                observed = int((output_dir / "progress").read_text(encoding="ascii"))
                if completed < observed <= len(indices):
                    completed = observed
                    if progress_callback:
                        progress_callback(completed, len(indices))
            except (FileNotFoundError, ValueError):
                pass
            time.sleep(0.05)
        check()
        payload = json.loads(process.stdout.read(4096))
        if process.returncode != 0:
            raise ConversionError(
                "conversion_failed", "The local rendering process stopped unexpectedly."
            )
        if "error" in payload:
            raise ConversionError(payload["error"], payload["message"])
        result = payload["result"]
        name = result["name"]
        media_type = result["media_type"]
        if name != Path(name).name or media_type not in {
            "image/jpeg",
            "application/zip",
        }:
            raise ConversionError(
                "conversion_failed", "The image result could not be verified."
            )
        path = output_dir / name
        enforce_output_size(path)
        (output_dir / "progress").unlink(missing_ok=True)
        spec_path.unlink(missing_ok=True)
        if progress_callback:
            progress_callback(len(indices), len(indices))
        if finalizing_callback:
            finalizing_callback()
        check()
        return JpegResult(path=path, media_type=media_type, download_name=name)
    except (PrivConError, JobCancelled):
        if process:
            _stop_worker(process)
        cleanup_now([output_dir])
        raise
    except Exception as exc:
        if process:
            _stop_worker(process)
        cleanup_now([output_dir])
        raise ConversionError(
            "conversion_failed", "The PDF could not be exported to JPEG images."
        ) from exc
    finally:
        if process:
            _stop_worker(process)
            if process.stdin:
                process.stdin.close()
            if process.stdout:
                process.stdout.close()
