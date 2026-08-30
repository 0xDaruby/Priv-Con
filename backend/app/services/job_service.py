"""In-memory lifecycle manager for truthful local conversion progress."""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from app.config import settings
from app.core.exceptions import (
    JobCapacityError,
    JobLookupError,
    PrivConError,
    ValidationError,
)
from app.core.file_utils import new_job_id, sanitize_filename
from app.core.logging_config import log_job_event
from app.core.progress import JobCancelled
from app.core.validators import (
    validate_image_structure,
    validate_office_structure,
    validate_pdf_structure,
)
from app.services import libreoffice_service
from app.services.cleanup_service import cleanup_now
from app.services.image_service import images_to_pdf
from app.services.pdf_merge_service import merge_pdfs
from app.services.pdf_split_service import (
    EVERY_PAGE_MODE,
    SplitResult,
    parse_page_ranges,
    split_pdf,
)

JobTool = Literal[
    "docx-to-pdf",
    "pptx-to-pdf",
    "xlsx-to-pdf",
    "pdf-merge",
    "pdf-split",
    "images-to-pdf",
]
JobStatus = Literal[
    "queued",
    "running",
    "succeeded",
    "failed",
    "cancelling",
    "cancelled",
]
JobStage = Literal[
    "queued",
    "validating",
    "converting",
    "finalizing",
    "ready",
    "cancelling",
    "cancelled",
    "failed",
]

TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}
OFFICE_TOOL_KEYS: dict[JobTool, str] = {
    "docx-to-pdf": "docx",
    "pptx-to-pdf": "pptx",
    "xlsx-to-pdf": "xlsx",
}
logger = logging.getLogger("privcon.jobs")


@dataclass(frozen=True)
class JobSpec:
    """Validated submission metadata kept only for the job lifecycle."""

    tool: JobTool
    input_paths: tuple[Path, ...]
    original_filenames: tuple[str, ...]
    mode: str | None = None
    ranges: str | None = None


@dataclass(frozen=True)
class JobSnapshot:
    job_id: str
    tool: JobTool
    status: JobStatus
    stage: JobStage
    message: str
    progress_percent: int | None
    completed_units: int | None
    total_units: int | None
    unit_label: str | None
    result_available: bool
    result_filename: str | None
    result_content_type: str | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class JobResultClaim:
    path: Path
    media_type: str
    download_name: str


@dataclass
class _JobRecord:
    job_id: str
    tool: JobTool
    status: JobStatus = "queued"
    stage: JobStage = "queued"
    message: str = "Waiting to start locally."
    progress_percent: int | None = None
    completed_units: int | None = None
    total_units: int | None = None
    unit_label: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    result_path: Path | None = None
    result_media_type: str | None = None
    result_download_name: str | None = None
    result_claimed: bool = False
    spec: JobSpec | None = None
    future: Future[None] | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    updated_at: float = field(default_factory=time.monotonic)


class JobManager:
    """Run bounded local jobs and expose thread-safe progress snapshots."""

    def __init__(self) -> None:
        self._records: dict[str, _JobRecord] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(
            max_workers=settings.max_concurrent_jobs,
            thread_name_prefix="privcon-job",
        )

    def reserve(self, tool: JobTool) -> str:
        """Reserve one bounded job slot before controlled upload persistence."""
        with self._lock:
            active_count = sum(
                record.status not in TERMINAL_STATUSES
                for record in self._records.values()
            )

            if active_count >= settings.max_concurrent_jobs:
                raise JobCapacityError(
                    code="server_busy",
                    message="The local converter is busy. Please retry shortly.",
                )

            job_id = new_job_id()
            self._records[job_id] = _JobRecord(job_id=job_id, tool=tool)

        log_job_event(logger, tool=tool, job_id=job_id, status="started")
        return job_id

    def start(self, job_id: str, spec: JobSpec) -> JobSnapshot:
        with self._lock:
            record = self._required_record(job_id)
            record.spec = spec
            record.future = self._executor.submit(self._run_job, job_id)
            return self._snapshot(record)

    def discard_submission(self, job_id: str, paths: tuple[Path, ...]) -> None:
        cleanup_now(paths)

        with self._lock:
            record = self._records.pop(job_id, None)

        if record is not None:
            log_job_event(
                logger,
                tool=record.tool,
                job_id=job_id,
                status="failure",
            )

    def get(self, job_id: str) -> JobSnapshot:
        with self._lock:
            return self._snapshot(self._required_record(job_id))

    def cancel(self, job_id: str) -> JobSnapshot:
        cleanup_targets: list[Path] = []

        with self._lock:
            record = self._required_record(job_id)

            if record.status in {"failed", "cancelled"}:
                return self._snapshot(record)

            record.cancel_event.set()

            if record.status == "succeeded":
                if record.result_path is not None:
                    cleanup_targets.append(record.result_path.parent)
                self._mark_cancelled(record)
                snapshot = self._snapshot(record)
            else:
                record.status = "cancelling"
                record.stage = "cancelling"
                record.message = "Stopping the local conversion."
                record.progress_percent = None
                record.completed_units = None
                record.total_units = None
                record.unit_label = None
                record.updated_at = time.monotonic()

                if record.future is not None and record.future.cancel():
                    if record.spec is not None:
                        cleanup_targets.extend(record.spec.input_paths)
                    self._mark_cancelled(record)

                snapshot = self._snapshot(record)

        cleanup_now(cleanup_targets)
        return snapshot

    def claim_result(self, job_id: str) -> JobResultClaim:
        with self._lock:
            record = self._required_record(job_id)

            if record.status != "succeeded":
                raise JobLookupError(
                    code="job_not_ready",
                    message="The conversion result is not ready yet.",
                )

            if (
                record.result_path is None
                or record.result_media_type is None
                or record.result_download_name is None
                or record.result_claimed
                or not record.result_path.is_file()
            ):
                raise JobLookupError(
                    code="result_unavailable",
                    message="This conversion result is no longer available.",
                )

            record.result_claimed = True
            return JobResultClaim(
                path=record.result_path,
                media_type=record.result_media_type,
                download_name=record.result_download_name,
            )

    def release_result_claim(self, job_id: str) -> None:
        with self._lock:
            record = self._records.get(job_id)

            if record is not None and record.result_path is not None:
                record.result_claimed = False

    def mark_result_delivered(self, job_id: str) -> None:
        cleanup_targets: list[Path] = []

        with self._lock:
            record = self._records.get(job_id)

            if record is None:
                return

            if record.result_path is not None:
                cleanup_targets.append(record.result_path.parent)

            record.result_path = None
            record.result_media_type = None
            record.result_download_name = None
            record.result_claimed = False
            record.updated_at = time.monotonic()

        cleanup_now(cleanup_targets)

    def sweep_expired_jobs(self) -> int:
        """Expire unclaimed results and old terminal status records."""
        cutoff = time.monotonic() - max(60, settings.cleanup_delay_minutes * 60)
        cleanup_targets: list[Path] = []
        expired_job_ids: list[str] = []

        with self._lock:
            for job_id, record in self._records.items():
                if record.status in TERMINAL_STATUSES and record.updated_at <= cutoff:
                    if record.result_path is not None:
                        cleanup_targets.append(record.result_path.parent)
                    expired_job_ids.append(job_id)

            for job_id in expired_job_ids:
                self._records.pop(job_id, None)

        cleanup_now(cleanup_targets)
        return len(expired_job_ids)

    def wait_for_idle(self, timeout: float = 5) -> bool:
        """Wait for active jobs; used by deterministic backend tests."""
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            with self._lock:
                if all(
                    record.status in TERMINAL_STATUSES
                    for record in self._records.values()
                ):
                    return True
            time.sleep(0.01)

        return False

    def _run_job(self, job_id: str) -> None:
        output_path: Path | None = None

        with self._lock:
            record = self._required_record(job_id)
            spec = record.spec

        if spec is None:
            self._fail(job_id, "internal_error", "The conversion could not start.")
            return

        try:
            self._set_stage(
                job_id,
                status="running",
                stage="validating",
                message="Checking the selected files locally.",
            )
            self._check_cancelled(job_id)

            if spec.tool in OFFICE_TOOL_KEYS:
                output_path, media_type, download_name = self._run_office(
                    job_id,
                    spec,
                )
            elif spec.tool == "pdf-merge":
                output_path, media_type, download_name = self._run_merge(
                    job_id,
                    spec,
                )
            elif spec.tool == "pdf-split":
                split_result = self._run_split(job_id, spec)
                output_path = split_result.path
                media_type = split_result.media_type
                download_name = split_result.download_name
            else:
                output_path, media_type, download_name = self._run_images(
                    job_id,
                    spec,
                )

            self._check_cancelled(job_id)
            cleanup_now(spec.input_paths)

            with self._lock:
                record = self._required_record(job_id)
                record.status = "succeeded"
                record.stage = "ready"
                record.message = "Your local conversion is ready to download."
                record.progress_percent = 100
                record.completed_units = record.total_units
                record.result_path = output_path
                record.result_media_type = media_type
                record.result_download_name = download_name
                record.result_claimed = False
                record.error_code = None
                record.error_message = None
                record.updated_at = time.monotonic()

            log_job_event(
                logger,
                tool=spec.tool,
                job_id=job_id,
                status="success",
            )
        except JobCancelled:
            cleanup_targets = [*spec.input_paths]

            if output_path is not None:
                cleanup_targets.append(output_path.parent)

            cleanup_now(cleanup_targets)

            with self._lock:
                record = self._records.get(job_id)
                if record is not None:
                    self._mark_cancelled(record)

            log_job_event(
                logger,
                tool=spec.tool,
                job_id=job_id,
                status="cancelled",
            )
        except PrivConError as exc:
            if output_path is not None:
                cleanup_now([*spec.input_paths, output_path.parent])
            else:
                cleanup_now(spec.input_paths)
            self._fail(job_id, exc.code, exc.message)
        except Exception:  # noqa: BLE001 - job boundary normalizes internals.
            if output_path is not None:
                cleanup_now([*spec.input_paths, output_path.parent])
            else:
                cleanup_now(spec.input_paths)
            self._fail(
                job_id,
                "file_processing_failed",
                "The selected files could not be processed.",
            )

    def _run_office(
        self,
        job_id: str,
        spec: JobSpec,
    ) -> tuple[Path, str, str]:
        tool_key = OFFICE_TOOL_KEYS[spec.tool]
        input_path = spec.input_paths[0]
        validate_office_structure(input_path, tool_key)
        self._set_progress(
            job_id,
            completed=1,
            total=1,
            unit_label="file",
            message="Validated 1 of 1 file.",
        )
        self._check_cancelled(job_id)
        self._set_stage(
            job_id,
            status="running",
            stage="converting",
            message="LibreOffice is converting the document locally.",
        )
        output_path = libreoffice_service.convert_to_pdf(
            input_path,
            job_id,
            cancellation_check=lambda: self._check_cancelled(job_id),
        )
        self._set_finalizing(job_id, "Checking the generated PDF locally.")
        safe_stem = sanitize_filename(Path(spec.original_filenames[0]).stem).strip(".")
        return output_path, "application/pdf", f"{safe_stem or 'document'}.pdf"

    def _run_merge(
        self,
        job_id: str,
        spec: JobSpec,
    ) -> tuple[Path, str, str]:
        total_pages = 0

        for index, path in enumerate(spec.input_paths, start=1):
            self._check_cancelled(job_id)
            total_pages += validate_pdf_structure(path)

            if total_pages > settings.max_pdf_pages_per_job:
                raise ValidationError(
                    code="too_many_pages",
                    message=(
                        "The combined PDFs exceed the safe page-count limit of "
                        f"{settings.max_pdf_pages_per_job} pages."
                    ),
                )

            self._set_progress(
                job_id,
                completed=index,
                total=len(spec.input_paths),
                unit_label="files",
                message=f"Validated {index} of {len(spec.input_paths)} files.",
            )

        self._set_stage(
            job_id,
            status="running",
            stage="converting",
            message=f"Merging 0 of {total_pages} pages.",
            progress_percent=0,
            completed_units=0,
            total_units=total_pages,
            unit_label="pages",
        )
        output_path = merge_pdfs(
            spec.input_paths,
            expected_total_pages=total_pages,
            progress_callback=lambda completed, total: self._set_progress(
                job_id,
                completed=completed,
                total=total,
                unit_label="pages",
                message=f"Merged {completed} of {total} pages.",
            ),
            finalizing_callback=lambda: self._set_finalizing(
                job_id,
                "Writing the merged PDF locally.",
            ),
            cancellation_check=lambda: self._check_cancelled(job_id),
        )
        return output_path, "application/pdf", "merged.pdf"

    def _run_split(self, job_id: str, spec: JobSpec) -> SplitResult:
        input_path = spec.input_paths[0]
        page_count = validate_pdf_structure(input_path)
        self._set_progress(
            job_id,
            completed=1,
            total=1,
            unit_label="file",
            message="Validated 1 of 1 file.",
        )
        self._check_cancelled(job_id)

        if spec.mode == EVERY_PAGE_MODE:
            total_units = page_count
            unit_label = "pages"
        else:
            total_units = len(parse_page_ranges(spec.ranges or "", page_count))
            unit_label = "ranges"

        self._set_stage(
            job_id,
            status="running",
            stage="converting",
            message=f"Splitting 0 of {total_units} {unit_label}.",
            progress_percent=0,
            completed_units=0,
            total_units=total_units,
            unit_label=unit_label,
        )
        return split_pdf(
            input_path=input_path,
            original_filename=spec.original_filenames[0],
            mode=spec.mode or "",
            ranges=spec.ranges,
            progress_callback=lambda completed, total: self._set_progress(
                job_id,
                completed=completed,
                total=total,
                unit_label=unit_label,
                message=f"Split {completed} of {total} {unit_label}.",
            ),
            finalizing_callback=lambda: self._set_finalizing(
                job_id,
                "Packaging the split result locally.",
            ),
            cancellation_check=lambda: self._check_cancelled(job_id),
        )

    def _run_images(
        self,
        job_id: str,
        spec: JobSpec,
    ) -> tuple[Path, str, str]:
        total_pixels = 0

        for index, (path, filename) in enumerate(
            zip(spec.input_paths, spec.original_filenames, strict=True),
            start=1,
        ):
            self._check_cancelled(job_id)
            total_pixels += validate_image_structure(path, filename)

            if total_pixels > settings.max_total_image_pixels:
                raise ValidationError(
                    code="oversized_file",
                    message=(
                        "The combined image dimensions exceed safe processing limits."
                    ),
                )

            self._set_progress(
                job_id,
                completed=index,
                total=len(spec.input_paths),
                unit_label="images",
                message=f"Validated {index} of {len(spec.input_paths)} images.",
            )

        self._set_stage(
            job_id,
            status="running",
            stage="converting",
            message=f"Preparing 0 of {len(spec.input_paths)} images.",
            progress_percent=0,
            completed_units=0,
            total_units=len(spec.input_paths),
            unit_label="images",
        )
        output_path = images_to_pdf(
            spec.input_paths,
            progress_callback=lambda completed, total: self._set_progress(
                job_id,
                completed=completed,
                total=total,
                unit_label="images",
                message=f"Prepared {completed} of {total} images.",
            ),
            finalizing_callback=lambda: self._set_finalizing(
                job_id,
                "Writing the image PDF locally.",
            ),
            cancellation_check=lambda: self._check_cancelled(job_id),
        )
        return output_path, "application/pdf", "images.pdf"

    def _set_progress(
        self,
        job_id: str,
        *,
        completed: int,
        total: int,
        unit_label: str,
        message: str,
    ) -> None:
        percent = round((completed / total) * 100) if total > 0 else 0

        with self._lock:
            record = self._required_record(job_id)
            record.progress_percent = max(0, min(100, percent))
            record.completed_units = max(0, completed)
            record.total_units = max(1, total)
            record.unit_label = unit_label
            record.message = message
            record.updated_at = time.monotonic()

    def _set_finalizing(self, job_id: str, message: str) -> None:
        self._set_stage(
            job_id,
            status="running",
            stage="finalizing",
            message=message,
        )

    def _set_stage(
        self,
        job_id: str,
        *,
        status: JobStatus,
        stage: JobStage,
        message: str,
        progress_percent: int | None = None,
        completed_units: int | None = None,
        total_units: int | None = None,
        unit_label: str | None = None,
    ) -> None:
        with self._lock:
            record = self._required_record(job_id)
            record.status = status
            record.stage = stage
            record.message = message
            record.progress_percent = progress_percent
            record.completed_units = completed_units
            record.total_units = total_units
            record.unit_label = unit_label
            record.updated_at = time.monotonic()

    def _check_cancelled(self, job_id: str) -> None:
        with self._lock:
            record = self._required_record(job_id)
            cancelled = record.cancel_event.is_set()

        if cancelled:
            raise JobCancelled

    def _fail(self, job_id: str, code: str, message: str) -> None:
        with self._lock:
            record = self._records.get(job_id)

            if record is None:
                return

            record.status = "failed"
            record.stage = "failed"
            record.message = message
            record.progress_percent = None
            record.completed_units = None
            record.total_units = None
            record.unit_label = None
            record.error_code = code
            record.error_message = message
            record.updated_at = time.monotonic()

        log_job_event(
            logger,
            tool=record.tool,
            job_id=job_id,
            status="failure",
        )

    @staticmethod
    def _mark_cancelled(record: _JobRecord) -> None:
        record.status = "cancelled"
        record.stage = "cancelled"
        record.message = "The local conversion was cancelled."
        record.progress_percent = None
        record.completed_units = None
        record.total_units = None
        record.unit_label = None
        record.result_path = None
        record.result_media_type = None
        record.result_download_name = None
        record.result_claimed = False
        record.updated_at = time.monotonic()

    def _required_record(self, job_id: str) -> _JobRecord:
        record = self._records.get(job_id)

        if record is None:
            raise JobLookupError(
                code="not_found",
                message="The requested conversion job was not found.",
            )

        return record

    @staticmethod
    def _snapshot(record: _JobRecord) -> JobSnapshot:
        return JobSnapshot(
            job_id=record.job_id,
            tool=record.tool,
            status=record.status,
            stage=record.stage,
            message=record.message,
            progress_percent=record.progress_percent,
            completed_units=record.completed_units,
            total_units=record.total_units,
            unit_label=record.unit_label,
            result_available=(
                record.status == "succeeded"
                and record.result_path is not None
                and not record.result_claimed
            ),
            result_filename=record.result_download_name,
            result_content_type=record.result_media_type,
            error_code=record.error_code,
            error_message=record.error_message,
        )


job_manager = JobManager()
