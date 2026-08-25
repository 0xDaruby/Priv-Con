"""Ordered image-to-PDF conversion using Pillow."""

import shutil
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings
from app.core.exceptions import PrivConError
from app.core.file_utils import new_job_id, output_dir_for_job


class ImageConversionError(PrivConError):
    """Raised when validated images cannot be converted into a PDF."""


def images_to_pdf(input_paths: Sequence[Path]) -> Path:
    """Convert images to one PDF, preserving upload order and dimensions."""
    if not input_paths:
        raise ImageConversionError(
            code="invalid_input",
            message="Upload at least one image to convert.",
        )

    job_id = new_job_id()
    output_dir = output_dir_for_job(settings.output_temp_dir, job_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "images.pdf"
    prepared_images: list[Image.Image] = []

    try:
        for input_path in input_paths:
            if not input_path.is_file():
                raise ImageConversionError(
                    code="conversion_failed",
                    message="An uploaded image could not be found for conversion.",
                )

            prepared_images.append(load_image_for_pdf(input_path))

        first_image, *remaining_images = prepared_images
        first_image.save(
            output_path,
            format="PDF",
            save_all=True,
            append_images=remaining_images,
            resolution=72.0,
        )

        with output_path.open("rb") as generated_pdf:
            if generated_pdf.read(5) != b"%PDF-":
                raise ImageConversionError(
                    code="conversion_failed",
                    message="The images could not be converted to PDF.",
                )

        return output_path
    except ImageConversionError:
        _cleanup_dir(output_dir)
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        _cleanup_dir(output_dir)
        raise ImageConversionError(
            code="conversion_failed",
            message="The images could not be converted to PDF.",
        ) from exc
    except Exception as exc:
        _cleanup_dir(output_dir)
        raise ImageConversionError(
            code="conversion_failed",
            message="The images could not be converted to PDF.",
        ) from exc
    finally:
        for image in prepared_images:
            image.close()


def load_image_for_pdf(input_path: Path) -> Image.Image:
    """Load, orient, and flatten one image into an independent RGB image."""
    with Image.open(input_path) as source_image:
        source_image.seek(0)
        oriented_image = ImageOps.exif_transpose(source_image)

        try:
            oriented_image.load()

            has_transparency = (
                oriented_image.mode in {"RGBA", "LA", "PA"}
                or (
                    oriented_image.mode == "P"
                    and "transparency" in oriented_image.info
                )
            )

            if not has_transparency:
                return oriented_image.convert("RGB")

            rgba_image = oriented_image.convert("RGBA")

            try:
                flattened_image = Image.new("RGB", rgba_image.size, "white")
                flattened_image.paste(
                    rgba_image,
                    mask=rgba_image.getchannel("A"),
                )
                return flattened_image
            finally:
                rgba_image.close()
        finally:
            oriented_image.close()


def _cleanup_dir(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)
