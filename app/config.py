from typing import Literal, cast

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"]
_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "/data/tokens.env"), env_file_encoding="utf-8"
    )

    trakt_client_id: str
    trakt_client_secret: str
    trakt_access_token: str
    trakt_refresh_token: str
    trakt_username: str

    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    smtp_from: str
    smtp_to: str

    discount_threshold_percent: float = Field(default=20.0, gt=0, le=100)
    check_interval_hours: float = Field(default=24.0, gt=0)
    api_request_interval_seconds: float = Field(default=2.0, ge=0)
    db_path: str = "/data/prices.db"
    log_level: LogLevel = "INFO"

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> LogLevel:
        if isinstance(value, str):
            normalized = value.upper()
            if normalized in _LOG_LEVELS:
                return cast(LogLevel, normalized)
        msg = "LOG_LEVEL must be one of CRITICAL, ERROR, WARNING, INFO, DEBUG, or NOTSET"
        raise ValueError(msg)


settings = Settings()  # type: ignore[call-arg]
