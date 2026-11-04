"""Environment-backed configuration for PerfAI."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
    new_relic_region: str = os.getenv("NEW_RELIC_REGION", "US").upper()
    new_relic_account_id: str = os.getenv("NEW_RELIC_ACCOUNT_ID", "")
    new_relic_api_key: str = os.getenv("NEW_RELIC_API_KEY", "")
    max_upload_mb: int = int(os.getenv("PERFAI_MAX_UPLOAD_MB", "100"))
    default_bucket_seconds: int = int(os.getenv("PERFAI_DEFAULT_BUCKET_SECONDS", "60"))


settings = Settings()
