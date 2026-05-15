from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def notify_module(monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.setenv("TRAKT_CLIENT_ID", "client-id")
    monkeypatch.setenv("TRAKT_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("TRAKT_ACCESS_TOKEN", "access-token")
    monkeypatch.setenv("TRAKT_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setenv("TRAKT_USERNAME", "username")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "smtp-user")
    monkeypatch.setenv("SMTP_PASSWORD", "smtp-password")
    monkeypatch.setenv("SMTP_FROM", "sender@example.com")
    monkeypatch.setenv("SMTP_TO", "recipient@example.com")

    import notify

    return notify


def test_send_alert_sends_plain_text_email(notify_module: object) -> None:
    notify_module.settings = SimpleNamespace(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="smtp-user",
        smtp_password="smtp-password",
        smtp_from="sender@example.com",
        smtp_to="recipient@example.com",
    )
    smtp = MagicMock()
    smtp_context = MagicMock()
    smtp_context.__enter__.return_value = smtp

    with patch.object(notify_module.smtplib, "SMTP", return_value=smtp_context) as smtp_class:
        notify_module.send_alert("Price drop", "The price dropped to $7.99.")

    smtp_class.assert_called_once_with("smtp.example.com", 587)
    smtp.starttls.assert_called_once_with()
    smtp.login.assert_called_once_with("smtp-user", "smtp-password")
    smtp.sendmail.assert_called_once()

    from_address, to_address, raw_message = smtp.sendmail.call_args.args
    assert from_address == "sender@example.com"
    assert to_address == "recipient@example.com"
    assert "Subject: Price drop" in raw_message
    assert "From: sender@example.com" in raw_message
    assert "To: recipient@example.com" in raw_message
    assert "Content-Type: text/plain" in raw_message
    assert "The price dropped to $7.99." in raw_message
