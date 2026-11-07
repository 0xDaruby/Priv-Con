"""Owned, killable local renderer. Invoked only by pdf_to_image_service."""

import json
import math
import sys
import zipfile
from pathlib import Path

import pymupdf
from PIL import Image


class RenderFailure(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def render_pages(spec: dict) -> dict[str, str]:
    """Preflight all selected dimensions, then render one RGB page at a time."""
    output_dir = Path(spec["output_dir"])
    input_path = Path(spec["input_path"])
    dpi = spec["dpi"]
    quality = spec["quality"]
    indices = spec["indices"]
    generated: list[Path] = []
    total_bytes = 0
    max_bytes = spec["max_bytes"]
    with pymupdf.open(input_path) as document:
        if (
            document.is_encrypted
            or document.is_repaired
            or len(document) != spec["page_count"]
        ):
            raise RenderFailure(
                "conversion_failed", "The PDF could not be rendered safely."
            )
        aggregate_pixels = 0
        expected_sizes: list[tuple[int, int]] = []
        for index in indices:
            rectangle = document[index].rect
            dimensions = (rectangle.width, rectangle.height)
            if any(not math.isfinite(value) or value <= 0 for value in dimensions):
                raise RenderFailure(
                    "render_too_large",
                    "The PDF page dimensions cannot be rendered safely.",
                )
            # MuPDF rounds transformed bounding rectangles outwards. Use its
            # geometry without allocating pixels, rather than assuming ceil(w).
            bounds = (rectangle * pymupdf.Matrix(dpi / 72, dpi / 72)).irect
            width, height = bounds.width, bounds.height
            pixels = width * height
            aggregate_pixels += pixels
            if (
                width <= 0
                or height <= 0
                or pixels > spec["max_page_pixels"]
                or aggregate_pixels > spec["max_total_pixels"]
            ):
                raise RenderFailure(
                    "render_too_large",
                    "The selected pages exceed safe rendering limits. Use fewer pages or a lower DPI.",
                )
            expected_sizes.append((width, height))
        padding = max(3, len(str(len(document))))
        for completed, (index, expected_size) in enumerate(
            zip(indices, expected_sizes, strict=True), 1
        ):
            path = output_dir / f"{spec['stem']}_page_{index + 1:0{padding}d}.jpg"
            pixmap = document[index].get_pixmap(
                dpi=dpi, colorspace=pymupdf.csRGB, alpha=False
            )
            try:
                if (pixmap.width, pixmap.height) != expected_size:
                    raise RenderFailure(
                        "conversion_failed",
                        "The rendered page dimensions could not be verified.",
                    )
                # A single page is encoded at a time, then its pixels released.
                pixmap.save(path, output="jpg", jpg_quality=quality)
            finally:
                del pixmap
            total_bytes += path.stat().st_size
            if total_bytes > max_bytes:
                raise RenderFailure(
                    "output_too_large",
                    "The generated images exceed the safe output size limit.",
                )
            with Image.open(path) as image:
                if image.format != "JPEG" or image.size != expected_size:
                    raise RenderFailure(
                        "conversion_failed", "The generated JPEG could not be verified."
                    )
                image.verify()
            generated.append(path)
            (output_dir / "progress").write_text(str(completed), encoding="ascii")
        if len(generated) == 1:
            path = generated[0]
            return {"name": path.name, "media_type": "image/jpeg"}
        archive_path = output_dir / f"{spec['stem']}_images.zip"
        with zipfile.ZipFile(
            archive_path, "x", compression=zipfile.ZIP_STORED
        ) as archive:
            for path in generated:
                archive.write(path, arcname=path.name)
                if archive_path.stat().st_size > max_bytes:
                    raise RenderFailure(
                        "output_too_large",
                        "The generated ZIP exceeds the safe output size limit.",
                    )
        if archive_path.stat().st_size > max_bytes:
            raise RenderFailure(
                "output_too_large",
                "The generated ZIP exceeds the safe output size limit.",
            )
        with zipfile.ZipFile(archive_path) as archive:
            if archive.testzip() is not None or archive.namelist() != [
                path.name for path in generated
            ]:
                raise RenderFailure(
                    "conversion_failed", "The generated ZIP could not be verified."
                )
        for path in generated:
            path.unlink()
        return {"name": archive_path.name, "media_type": "application/zip"}


def main() -> None:
    try:
        # The coordinator creates this file inside its private job directory.
        # Never read unbounded metadata or wait on a pipe before rendering.
        with Path(sys.argv[1]).open("r", encoding="utf-8") as stream:
            spec = json.loads(stream.read(64 * 1024))
        result = render_pages(spec)
        print(json.dumps({"result": result}), flush=True)
    except RenderFailure as exc:
        print(json.dumps({"error": exc.code, "message": exc.message}), flush=True)
    except Exception:  # noqa: BLE001 - normalize errors at the child-process boundary.
        # Internal paths/parser diagnostics never cross the process boundary.
        print(
            json.dumps(
                {
                    "error": "conversion_failed",
                    "message": "The PDF could not be exported to JPEG images.",
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
