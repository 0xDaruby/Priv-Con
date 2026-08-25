"""PDF split service supporting per-page and page-range modes."""

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from app.config import settings
from app.core.exceptions import PrivConError, ValidationError
from app.core.file_utils import (
    enforce_output_size,
    ensure_private_directory,
    new_job_id,
    output_dir_for_job,
    private_binary_writer,
    sanitize_filename,
)
from app.services.cleanup_service import cleanup_now, mark_active_paths

EVERY_PAGE_MODE = "every_page"
RANGES_MODE = "ranges"
SPLIT_MODES = {EVERY_PAGE_MODE, RANGES_MODE}
_RANGE_PATTERN = re.compile(r"^(\d+)(?:\s*-\s*(\d+))?$")


class SplitError(PrivConError):
    """Raised for invalid split options or failed PDF output generation."""


@dataclass(frozen=True)
class PageRange:
    start: int
    end: int


@dataclass(frozen=True)
class SplitResult:
    path: Path
    media_type: str
    download_name: str


def validate_split_options(mode: str, ranges: str | None) -> None:
    """Validate mode-dependent fields that do not require reading the PDF."""
    if mode not in SPLIT_MODES:
        raise SplitError(
            code="invalid_split_mode",
            message="Split mode must be either 'every_page' or 'ranges'.",
        )

    has_ranges = bool(ranges and ranges.strip())

    if mode == EVERY_PAGE_MODE and has_ranges:
        raise SplitError(
            code="invalid_page_ranges",
            message="Page ranges cannot be used with every_page mode.",
        )

    if mode == RANGES_MODE and not has_ranges:
        raise SplitError(
            code="invalid_page_ranges",
            message="Provide at least one page range when using ranges mode.",
        )


def parse_page_ranges(raw_ranges: str, page_count: int) -> list[PageRange]:
    """Parse one-based inclusive ranges and reject ambiguous page selection."""
    tokens = raw_ranges.split(",")

    if not tokens or any(not token.strip() for token in tokens):
        raise SplitError(
            code="invalid_page_ranges",
            message="Page ranges must use a format such as 1-3,5,8-10.",
        )

    parsed_ranges: list[PageRange] = []
    selected_pages: set[int] = set()

    for token in tokens:
        match = _RANGE_PATTERN.fullmatch(token.strip())

        if match is None:
            raise SplitError(
                code="invalid_page_ranges",
                message="Page ranges must use a format such as 1-3,5,8-10.",
            )

        start = int(match.group(1))
        end = int(match.group(2) or start)

        if start <= 0 or end <= 0:
            raise SplitError(
                code="invalid_page_ranges",
                message="Page numbers must be positive and start at 1.",
            )

        if end < start:
            raise SplitError(
                code="invalid_page_ranges",
                message="Page range end values cannot be less than their starts.",
            )

        if end > page_count:
            raise SplitError(
                code="invalid_page_ranges",
                message=f"Page ranges cannot exceed page {page_count}.",
            )

        pages = set(range(start, end + 1))

        if selected_pages.intersection(pages):
            raise SplitError(
                code="invalid_page_ranges",
                message="Page ranges cannot overlap or select duplicate pages.",
            )

        selected_pages.update(pages)
        parsed_ranges.append(PageRange(start=start, end=end))

    return parsed_ranges


def split_pdf(
    input_path: Path,
    original_filename: str,
    mode: str,
    ranges: str | None,
) -> SplitResult:
    """Split a validated PDF and return either a PDF or ZIP result."""
    validate_split_options(mode, ranges)

    job_id = new_job_id()
    output_dir = output_dir_for_job(settings.output_temp_dir, job_id)
    ensure_private_directory(output_dir)
    mark_active_paths([output_dir])
    reader: PdfReader | None = None

    try:
        reader = PdfReader(str(input_path), strict=True)

        if reader.is_encrypted:
            raise SplitError(
                code="password_protected",
                message="Password-protected PDFs are not supported.",
            )

        page_count = len(reader.pages)

        if page_count == 0:
            raise SplitError(
                code="empty_pdf",
                message="PDF files must contain at least one page.",
            )

        if page_count > settings.max_pdf_pages_per_job:
            raise SplitError(
                code="too_many_pages",
                message=(
                    "The PDF exceeds the safe page-count limit of "
                    f"{settings.max_pdf_pages_per_job} pages."
                ),
            )

        safe_stem = _sanitized_stem(original_filename)

        if mode == EVERY_PAGE_MODE:
            page_ranges = [PageRange(page, page) for page in range(1, page_count + 1)]
            generated_paths = _write_every_page(
                reader=reader,
                page_ranges=page_ranges,
                output_dir=output_dir,
                safe_stem=safe_stem,
                page_count=page_count,
            )
        else:
            page_ranges = parse_page_ranges(ranges or "", page_count)
            generated_paths = _write_ranges(
                reader=reader,
                page_ranges=page_ranges,
                output_dir=output_dir,
                safe_stem=safe_stem,
            )

        if mode == RANGES_MODE and len(generated_paths) == 1:
            result_path = generated_paths[0]
            _enforce_output_limit(result_path)
            return SplitResult(
                path=result_path,
                media_type="application/pdf",
                download_name=result_path.name,
            )

        zip_path = output_dir / f"{safe_stem}_split.zip"

        with (
            private_binary_writer(zip_path) as zip_file,
            zipfile.ZipFile(
                zip_file,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive,
        ):
            for generated_path in generated_paths:
                archive.write(generated_path, arcname=generated_path.name)

        _enforce_output_limit(zip_path)

        for generated_path in generated_paths:
            generated_path.unlink(missing_ok=True)

        return SplitResult(
            path=zip_path,
            media_type="application/zip",
            download_name=zip_path.name,
        )
    except SplitError:
        _cleanup_dir(output_dir)
        raise
    except Exception as exc:
        _cleanup_dir(output_dir)
        raise SplitError(
            code="split_failed",
            message="The PDF could not be split.",
        ) from exc
    finally:
        if reader is not None:
            reader.close()


def _write_every_page(
    reader: PdfReader,
    page_ranges: list[PageRange],
    output_dir: Path,
    safe_stem: str,
    page_count: int,
) -> list[Path]:
    padding = max(3, len(str(page_count)))
    generated_paths: list[Path] = []

    for page_range in page_ranges:
        filename = f"{safe_stem}_page_{page_range.start:0{padding}d}.pdf"
        output_path = output_dir / filename
        _write_range(reader, page_range, output_path)
        generated_paths.append(output_path)
        _enforce_total_generated_size(generated_paths)

    return generated_paths


def _write_ranges(
    reader: PdfReader,
    page_ranges: list[PageRange],
    output_dir: Path,
    safe_stem: str,
) -> list[Path]:
    generated_paths: list[Path] = []

    for page_range in page_ranges:
        filename = f"{safe_stem}_pages_{page_range.start}-{page_range.end}.pdf"
        output_path = output_dir / filename
        _write_range(reader, page_range, output_path)
        generated_paths.append(output_path)
        _enforce_total_generated_size(generated_paths)

    return generated_paths


def _write_range(
    reader: PdfReader,
    page_range: PageRange,
    output_path: Path,
) -> None:
    writer = PdfWriter()

    try:
        for page_number in range(page_range.start, page_range.end + 1):
            writer.add_page(reader.pages[page_number - 1])

        with private_binary_writer(output_path) as output_file:
            writer.write(output_file)
    finally:
        writer.close()


def _sanitized_stem(filename: str) -> str:
    stem = Path(filename or "document.pdf").stem
    safe_stem = sanitize_filename(stem).strip(".")
    return safe_stem or "document"


def _enforce_total_generated_size(paths: list[Path]) -> None:
    max_output_bytes = settings.max_output_size_mb * 1024 * 1024

    try:
        total_size = sum(path.stat().st_size for path in paths)
    except OSError as exc:
        raise SplitError(
            code="split_failed",
            message="The generated PDF output could not be inspected.",
        ) from exc

    if total_size > max_output_bytes:
        raise SplitError(
            code="output_too_large",
            message=(
                "The generated output exceeds the safe processing limit. "
                "Use fewer pages or ranges."
            ),
        )


def _enforce_output_limit(path: Path) -> None:
    try:
        enforce_output_size(path)
    except ValidationError as exc:
        raise SplitError(code=exc.code, message=exc.message) from exc


def _cleanup_dir(path: Path) -> None:
    cleanup_now([path])
