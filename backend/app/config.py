"""Application settings, loaded from environment / .env.

Mirrors backend/.env.example from setup.md section 4.
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    upload_temp_dir: Path = Path("./temp/uploads")
    output_temp_dir: Path = Path("./temp/outputs")
    max_upload_size_mb: int = 50
    conversion_timeout_seconds: int = 60
    cleanup_mode: str = "immediate"  # immediate | delayed
    cleanup_delay_minutes: int = 10
    libreoffice_path: str = "libreoffice"
    cors_origin: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
settings.upload_temp_dir.mkdir(parents=True, exist_ok=True)
settings.output_temp_dir.mkdir(parents=True, exist_ok=True)
