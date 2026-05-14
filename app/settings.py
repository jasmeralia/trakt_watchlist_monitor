from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "/app/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    check_interval_hours: int = 24


settings = Settings()
