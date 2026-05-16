import pytest
from pydantic import ValidationError

from config import Settings


def test_log_level_defaults_to_info() -> None:
    assert _settings().log_level == "INFO"


def test_api_request_interval_defaults_to_two_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_REQUEST_INTERVAL_SECONDS", raising=False)

    assert _settings().api_request_interval_seconds == 2.0


def test_api_request_interval_accepts_zero_to_disable_sleep() -> None:
    assert _settings(api_request_interval_seconds=0).api_request_interval_seconds == 0.0


def test_log_level_accepts_lowercase_value() -> None:
    assert _settings(log_level="debug").log_level == "DEBUG"


def test_log_level_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError, match="LOG_LEVEL must be one of"):
        _settings(log_level="verbose")


def _settings(**overrides: object) -> Settings:
    values = {
        "trakt_client_id": "client-id",
        "trakt_client_secret": "client-secret",
        "trakt_access_token": "access-token",
        "trakt_refresh_token": "refresh-token",
        "trakt_username": "username",
        "smtp_host": "smtp.example.com",
        "smtp_username": "smtp-user",
        "smtp_password": "smtp-password",
        "smtp_from": "from@example.com",
        "smtp_to": "to@example.com",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]
