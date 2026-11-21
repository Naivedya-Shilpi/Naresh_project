"""Configuration for the local FastAPI service."""

from dataclasses import dataclass
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = f"sqlite:///{PROJECT_ROOT / 'storage' / 'meeting_transcriber.db'}"


@dataclass(frozen=True)
class Settings:
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
    database_url: str = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    whisper_model: str = os.getenv("WHISPER_MODEL", "base")
    whisper_device: str = os.getenv("WHISPER_DEVICE", "cpu")
    whisper_compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    pyannote_model: str = os.getenv("PYANNOTE_MODEL", "pyannote/speaker-diarization-3.1")
    pyannote_auth_token: str | None = os.getenv("PYANNOTE_AUTH_TOKEN") or None


settings = Settings()
