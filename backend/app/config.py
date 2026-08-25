"""Application settings, loaded from environment / .env.

Mirrors backend/.env.example from setup.md section 4.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    upload_temp_dir: Path = Path("./temp/uploads")
    output_temp_dir: Path = Path("./temp/outputs")
    max_upload_size_mb: int = Field(default=50, gt=0)
    conversion_timeout_seconds: int = Field(default=60, gt=0)
    cleanup_mode: Literal["immediate", "delayed"] = "immediate"
    cleanup_delay_minutes: int = Field(default=10, gt=0)
    libreoffice_path: str = "libreoffice"
    cors_origin: str = "http://localhost:3000"


settings = Settings()
settings.upload_temp_dir.mkdir(parents=True, exist_ok=True)
settings.output_temp_dir.mkdir(parents=True, exist_ok=True)
