from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "QuestPilot"
    app_env: str = "development"
    app_api_key: str = ""
    database_url: str = "sqlite+pysqlite:///./questpilot.db"
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    model_provider: str = "fake"
    model_base_url: str = "https://api.openai.com/v1"
    model_api_key: str = ""
    model_name: str = "gpt-4.1-mini"
    model_thinking_enabled: bool = False
    model_fallbacks: str = ""
    atlas_base_url: str = "https://api.atlasacademy.io"
    data_dir: Path = Field(default=Path("./data"))
    pgvector_enabled: bool = False
    redis_url: str = ""
    object_storage_endpoint: str = ""
    object_storage_bucket: str = "questpilot"
    object_storage_access_key: str = ""
    object_storage_secret_key: str = ""
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def fallback_model_list(self) -> list[str]:
        return [item.strip() for item in self.model_fallbacks.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
