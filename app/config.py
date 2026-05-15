from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

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
    db_path: str = "/data/prices.db"


settings = Settings()  # type: ignore[call-arg]
