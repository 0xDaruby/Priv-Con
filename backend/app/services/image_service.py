"""Ordered image-to-PDF conversion using Pillow."""

import warnings
from collections.abc import Sequence
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings
from app.core.exceptions import PrivConError, ValidationError
from app.core.file_utils import (
    enforce_output_size,
    ensure_private_directory,
    new_job_id,
    output_dir_for_job,
    private_binary_writer,
)
from app.services.cleanup_service import cleanup_now, mark_active_paths


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
    ensure_private_directory(output_dir)
    mark_active_paths([output_dir])
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
        with private_binary_writer(output_path) as output_file:
            first_image.save(
                output_file,
                format="PDF",
                save_all=True,
                append_images=remaining_images,
                resolution=72.0,
            )

        try:
            enforce_output_size(output_path)
        except ValidationError as exc:
            raise ImageConversionError(code=exc.code, message=exc.message) from exc

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
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)

        with Image.open(
            input_path,
            formats=["JPEG", "PNG", "WEBP"],
        ) as source_image:
            source_image.seek(0)

            if source_image.width * source_image.height > settings.max_image_pixels:
                raise ImageConversionError(
                    code="oversized_file",
                    message="The image dimensions exceed safe processing limits.",
                )

            oriented_image = ImageOps.exif_transpose(source_image)

            try:
                oriented_image.load()

                has_transparency = oriented_image.mode in {"RGBA", "LA", "PA"} or (
                    oriented_image.mode == "P" and "transparency" in oriented_image.info
                )

                if not has_transparency:
                    prepared_image = oriented_image.convert("RGB")
                    prepared_image.info.clear()
                    return prepared_image

                rgba_image = oriented_image.convert("RGBA")

                try:
                    flattened_image = Image.new("RGB", rgba_image.size, "white")
                    flattened_image.paste(
                        rgba_image,
                        mask=rgba_image.getchannel("A"),
                    )
                    flattened_image.info.clear()
                    return flattened_image
                finally:
                    rgba_image.close()
            finally:
                oriented_image.close()


def _cleanup_dir(path: Path) -> None:
    cleanup_now([path])
