"""Application settings, loaded from environment / .env.

Mirrors backend/.env.example from setup.md section 4.
"""

from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    upload_temp_dir: Path = Path("./temp/uploads")
    output_temp_dir: Path = Path("./temp/outputs")
    max_upload_size_mb: int = Field(default=50, gt=0)
    max_total_upload_size_mb: int = Field(default=200, gt=0)
    max_request_size_mb: int = Field(default=205, gt=0)
    max_output_size_mb: int = Field(default=500, gt=0)
    max_files_per_request: int = Field(default=20, gt=0, le=100)
    max_form_fields_per_request: int = Field(default=10, gt=0, le=100)
    max_form_field_size_kb: int = Field(default=16, gt=0, le=1024)
    max_concurrent_jobs: int = Field(default=2, gt=0, le=32)
    max_pdf_pages_per_job: int = Field(default=2000, gt=0)
    max_image_pixels: int = Field(default=40_000_000, gt=0)
    max_total_image_pixels: int = Field(default=100_000_000, gt=0)
    max_office_archive_entries: int = Field(default=10_000, gt=0)
    max_office_uncompressed_size_mb: int = Field(default=250, gt=0)
    max_office_compression_ratio: int = Field(default=200, gt=0)
    conversion_timeout_seconds: int = Field(default=60, gt=0)
    cleanup_mode: Literal["immediate", "delayed"] = "immediate"
    cleanup_delay_minutes: int = Field(default=10, gt=0)
    libreoffice_path: str = "libreoffice"
    cors_origin: str = "http://localhost:3000"

    @field_validator("cors_origin")
    @classmethod
    def validate_cors_origin(cls, value: str) -> str:
        parsed = urlsplit(value)

        if (
            value == "*"
            or parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("cors_origin must be one exact HTTP(S) origin")

        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_resource_limits(self) -> "Settings":
        if self.max_total_upload_size_mb < self.max_upload_size_mb:
            raise ValueError(
                "max_total_upload_size_mb cannot be smaller than max_upload_size_mb"
            )

        if self.max_request_size_mb < self.max_total_upload_size_mb:
            raise ValueError(
                "max_request_size_mb cannot be smaller than max_total_upload_size_mb"
            )

        if self.max_total_image_pixels < self.max_image_pixels:
            raise ValueError(
                "max_total_image_pixels cannot be smaller than max_image_pixels"
            )

        upload_root = self.upload_temp_dir.resolve(strict=False)
        output_root = self.output_temp_dir.resolve(strict=False)

        if upload_root == output_root:
            raise ValueError("upload_temp_dir and output_temp_dir must be distinct")

        if upload_root in output_root.parents or output_root in upload_root.parents:
            raise ValueError("temporary roots must not contain one another")

        protected_roots = {
            Path(upload_root.anchor),
            Path.cwd().resolve(strict=False),
            Path.home().resolve(strict=False),
        }

        if upload_root in protected_roots or output_root in protected_roots:
            raise ValueError(
                "temporary roots cannot be a filesystem root, the working "
                "directory, or the user home directory"
            )

        return self


settings = Settings()
settings.upload_temp_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
settings.output_temp_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

for temp_root in (settings.upload_temp_dir, settings.output_temp_dir):
    temp_root.chmod(0o700)
