import smtplib
from unittest.mock import Mock

import pytest

import pricing
from pricing import meets_discount_threshold, select_best_quality


class FakeConnection:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class TestSelectBestQuality:
    def test_prefers_uhd_over_hd_and_sd(self) -> None:
        prices = [
            {"quality": "SD", "price": 9.99},
            {"quality": "HD", "price": 12.99},
            {"quality": "UHD", "price": 14.99},
        ]
        result = select_best_quality(prices)
        assert result is not None
        assert result["quality"] == "UHD"

    def test_prefers_hd_over_sd(self) -> None:
        prices = [
            {"quality": "SD", "price": 9.99},
            {"quality": "HD", "price": 12.99},
        ]
        result = select_best_quality(prices)
        assert result is not None
        assert result["quality"] == "HD"

    def test_single_sd_entry(self) -> None:
        prices = [{"quality": "SD", "price": 9.99}]
        result = select_best_quality(prices)
        assert result is not None
        assert result["quality"] == "SD"

    def test_empty_list_returns_none(self) -> None:
        assert select_best_quality([]) is None


class TestMeetsDiscountThreshold:
    def test_above_threshold(self) -> None:
        assert meets_discount_threshold(10.00, 7.00, 20.0) is True  # 30% drop

    def test_exactly_at_threshold(self) -> None:
        assert meets_discount_threshold(10.00, 8.00, 20.0) is True  # exactly 20%

    def test_below_threshold(self) -> None:
        assert meets_discount_threshold(10.00, 9.00, 20.0) is False  # 10% drop

    def test_no_discount(self) -> None:
        assert meets_discount_threshold(10.00, 10.00, 20.0) is False


class TestCheckPrices:
    def test_sends_alert_when_threshold_is_met(self, monkeypatch: pytest.MonkeyPatch) -> None:
        conn = FakeConnection()
        send_alert = Mock()
        log_notification = Mock()
        upsert_price = Mock()

        monkeypatch.setattr(pricing.settings, "db_path", ":memory:")
        monkeypatch.setattr(pricing.settings, "discount_threshold_percent", 20.0)
        monkeypatch.setattr(pricing.db, "init_db", Mock(return_value=conn))
        monkeypatch.setattr(
            pricing.trakt,
            "get_effective_watchlist",
            Mock(
                return_value=[
                    {
                        "trakt_id": 123,
                        "media_type": "movie",
                        "title": "Example Movie",
                        "tmdb_id": 456,
                    }
                ]
            ),
        )
        monkeypatch.setattr(
            pricing.justwatch,
            "get_amazon_prices",
            Mock(return_value=[{"quality": "HD", "price": 7.99, "currency": "USD"}]),
        )
        monkeypatch.setattr(pricing.db, "get_last_price", Mock(return_value=12.99))
        monkeypatch.setattr(pricing.db, "was_notified", Mock(return_value=False))
        monkeypatch.setattr(pricing.notify, "send_alert", send_alert)
        monkeypatch.setattr(pricing.db, "log_notification", log_notification)
        monkeypatch.setattr(pricing.db, "upsert_price", upsert_price)

        pricing.check_prices()

        send_alert.assert_called_once()
        log_notification.assert_called_once_with(conn, 123, "movie", "HD", 7.99, 12.99)
        upsert_price.assert_called_once_with(conn, 123, "movie", "HD", 7.99, "USD")
        assert conn.closed is True

    def test_does_not_send_alert_when_below_threshold(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        conn = FakeConnection()
        send_alert = Mock()
        log_notification = Mock()
        upsert_price = Mock()

        monkeypatch.setattr(pricing.settings, "db_path", ":memory:")
        monkeypatch.setattr(pricing.settings, "discount_threshold_percent", 20.0)
        monkeypatch.setattr(pricing.db, "init_db", Mock(return_value=conn))
        monkeypatch.setattr(
            pricing.trakt,
            "get_effective_watchlist",
            Mock(
                return_value=[
                    {
                        "trakt_id": 123,
                        "media_type": "movie",
                        "title": "Example Movie",
                        "tmdb_id": 456,
                    }
                ]
            ),
        )
        monkeypatch.setattr(
            pricing.justwatch,
            "get_amazon_prices",
            Mock(return_value=[{"quality": "HD", "price": 11.99, "currency": "USD"}]),
        )
        monkeypatch.setattr(pricing.db, "get_last_price", Mock(return_value=12.99))
        monkeypatch.setattr(pricing.db, "was_notified", Mock(return_value=False))
        monkeypatch.setattr(pricing.notify, "send_alert", send_alert)
        monkeypatch.setattr(pricing.db, "log_notification", log_notification)
        monkeypatch.setattr(pricing.db, "upsert_price", upsert_price)

        pricing.check_prices()

        send_alert.assert_not_called()
        log_notification.assert_not_called()
        upsert_price.assert_called_once_with(conn, 123, "movie", "HD", 11.99, "USD")
        assert conn.closed is True

    def test_first_observation_stores_price_without_alert(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        conn = FakeConnection()
        send_alert = Mock()
        log_notification = Mock()
        upsert_price = Mock()

        monkeypatch.setattr(pricing.settings, "db_path", ":memory:")
        monkeypatch.setattr(pricing.settings, "discount_threshold_percent", 20.0)
        monkeypatch.setattr(pricing.db, "init_db", Mock(return_value=conn))
        monkeypatch.setattr(
            pricing.trakt,
            "get_effective_watchlist",
            Mock(
                return_value=[
                    {
                        "trakt_id": 123,
                        "media_type": "movie",
                        "title": "Example Movie",
                        "tmdb_id": 456,
                    }
                ]
            ),
        )
        monkeypatch.setattr(
            pricing.justwatch,
            "get_amazon_prices",
            Mock(return_value=[{"quality": "HD", "price": 7.99, "currency": "USD"}]),
        )
        monkeypatch.setattr(pricing.db, "get_last_price", Mock(return_value=None))
        monkeypatch.setattr(pricing.db, "was_notified", Mock(return_value=False))
        monkeypatch.setattr(pricing.notify, "send_alert", send_alert)
        monkeypatch.setattr(pricing.db, "log_notification", log_notification)
        monkeypatch.setattr(pricing.db, "upsert_price", upsert_price)

        pricing.check_prices()

        send_alert.assert_not_called()
        log_notification.assert_not_called()
        upsert_price.assert_called_once_with(conn, 123, "movie", "HD", 7.99, "USD")
        assert conn.closed is True

    def test_does_not_send_duplicate_alert_when_already_notified(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        conn = FakeConnection()
        send_alert = Mock()
        log_notification = Mock()
        upsert_price = Mock()

        monkeypatch.setattr(pricing.settings, "db_path", ":memory:")
        monkeypatch.setattr(pricing.settings, "discount_threshold_percent", 20.0)
        monkeypatch.setattr(pricing.db, "init_db", Mock(return_value=conn))
        monkeypatch.setattr(
            pricing.trakt,
            "get_effective_watchlist",
            Mock(
                return_value=[
                    {
                        "trakt_id": 123,
                        "media_type": "movie",
                        "title": "Example Movie",
                        "tmdb_id": 456,
                    }
                ]
            ),
        )
        monkeypatch.setattr(
            pricing.justwatch,
            "get_amazon_prices",
            Mock(return_value=[{"quality": "HD", "price": 7.99, "currency": "USD"}]),
        )
        monkeypatch.setattr(pricing.db, "get_last_price", Mock(return_value=12.99))
        monkeypatch.setattr(pricing.db, "was_notified", Mock(return_value=True))
        monkeypatch.setattr(pricing.notify, "send_alert", send_alert)
        monkeypatch.setattr(pricing.db, "log_notification", log_notification)
        monkeypatch.setattr(pricing.db, "upsert_price", upsert_price)

        pricing.check_prices()

        send_alert.assert_not_called()
        log_notification.assert_not_called()
        upsert_price.assert_called_once_with(conn, 123, "movie", "HD", 7.99, "USD")
        assert conn.closed is True

    def test_skips_item_with_no_justwatch_prices(self, monkeypatch: pytest.MonkeyPatch) -> None:
        conn = FakeConnection()
        send_alert = Mock()
        upsert_price = Mock()

        monkeypatch.setattr(pricing.settings, "db_path", ":memory:")
        monkeypatch.setattr(pricing.db, "init_db", Mock(return_value=conn))
        monkeypatch.setattr(
            pricing.trakt,
            "get_effective_watchlist",
            Mock(
                return_value=[
                    {
                        "trakt_id": 123,
                        "media_type": "movie",
                        "title": "Example Movie",
                        "tmdb_id": 456,
                    }
                ]
            ),
        )
        monkeypatch.setattr(pricing.justwatch, "get_amazon_prices", Mock(return_value=[]))
        monkeypatch.setattr(pricing.notify, "send_alert", send_alert)
        monkeypatch.setattr(pricing.db, "upsert_price", upsert_price)

        pricing.check_prices()

        send_alert.assert_not_called()
        upsert_price.assert_not_called()
        assert conn.closed is True

    def test_skips_item_without_tmdb_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        conn = FakeConnection()
        send_alert = Mock()
        get_amazon_prices = Mock()
        upsert_price = Mock()

        monkeypatch.setattr(pricing.settings, "db_path", ":memory:")
        monkeypatch.setattr(pricing.db, "init_db", Mock(return_value=conn))
        monkeypatch.setattr(
            pricing.trakt,
            "get_effective_watchlist",
            Mock(
                return_value=[
                    {
                        "trakt_id": 123,
                        "media_type": "movie",
                        "title": "Example Movie",
                        "tmdb_id": None,
                    }
                ]
            ),
        )
        monkeypatch.setattr(pricing.justwatch, "get_amazon_prices", get_amazon_prices)
        monkeypatch.setattr(pricing.notify, "send_alert", send_alert)
        monkeypatch.setattr(pricing.db, "upsert_price", upsert_price)

        pricing.check_prices()

        get_amazon_prices.assert_not_called()
        send_alert.assert_not_called()
        upsert_price.assert_not_called()
        assert conn.closed is True

    def test_stores_price_increase_without_alert(self, monkeypatch: pytest.MonkeyPatch) -> None:
        conn = FakeConnection()
        send_alert = Mock()
        log_notification = Mock()
        upsert_price = Mock()

        monkeypatch.setattr(pricing.settings, "db_path", ":memory:")
        monkeypatch.setattr(pricing.settings, "discount_threshold_percent", 20.0)
        monkeypatch.setattr(pricing.db, "init_db", Mock(return_value=conn))
        monkeypatch.setattr(
            pricing.trakt,
            "get_effective_watchlist",
            Mock(
                return_value=[
                    {
                        "trakt_id": 123,
                        "media_type": "movie",
                        "title": "Example Movie",
                        "tmdb_id": 456,
                    }
                ]
            ),
        )
        monkeypatch.setattr(
            pricing.justwatch,
            "get_amazon_prices",
            Mock(return_value=[{"quality": "HD", "price": 14.99, "currency": "USD"}]),
        )
        monkeypatch.setattr(pricing.db, "get_last_price", Mock(return_value=12.99))
        monkeypatch.setattr(pricing.db, "was_notified", Mock(return_value=False))
        monkeypatch.setattr(pricing.notify, "send_alert", send_alert)
        monkeypatch.setattr(pricing.db, "log_notification", log_notification)
        monkeypatch.setattr(pricing.db, "upsert_price", upsert_price)

        pricing.check_prices()

        send_alert.assert_not_called()
        log_notification.assert_not_called()
        upsert_price.assert_called_once_with(conn, 123, "movie", "HD", 14.99, "USD")
        assert conn.closed is True

    def test_notification_failure_does_not_skip_price_upsert(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        conn = FakeConnection()
        send_alert = Mock(side_effect=smtplib.SMTPException("smtp failed"))
        log_notification = Mock()
        upsert_price = Mock()

        monkeypatch.setattr(pricing.settings, "db_path", ":memory:")
        monkeypatch.setattr(pricing.settings, "discount_threshold_percent", 20.0)
        monkeypatch.setattr(pricing.db, "init_db", Mock(return_value=conn))
        monkeypatch.setattr(
            pricing.trakt,
            "get_effective_watchlist",
            Mock(
                return_value=[
                    {
                        "trakt_id": 123,
                        "media_type": "movie",
                        "title": "Example Movie",
                        "tmdb_id": 456,
                    }
                ]
            ),
        )
        monkeypatch.setattr(
            pricing.justwatch,
            "get_amazon_prices",
            Mock(return_value=[{"quality": "HD", "price": 7.99, "currency": "USD"}]),
        )
        monkeypatch.setattr(pricing.db, "get_last_price", Mock(return_value=12.99))
        monkeypatch.setattr(pricing.db, "was_notified", Mock(return_value=False))
        monkeypatch.setattr(pricing.notify, "send_alert", send_alert)
        monkeypatch.setattr(pricing.db, "log_notification", log_notification)
        monkeypatch.setattr(pricing.db, "upsert_price", upsert_price)

        pricing.check_prices()

        send_alert.assert_called_once()
        log_notification.assert_not_called()
        upsert_price.assert_called_once_with(conn, 123, "movie", "HD", 7.99, "USD")
        assert "Failed to send price alert for 123: smtp failed" in capsys.readouterr().err
        assert conn.closed is True

    def test_item_failure_continues_to_next_item(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        conn = FakeConnection()
        send_alert = Mock()
        log_notification = Mock()
        upsert_price = Mock()

        def get_amazon_prices(tmdb_id: int, media_type: str) -> list[dict[str, object]]:
            if tmdb_id == 456:
                raise ValueError("bad justwatch response")
            return [{"quality": "HD", "price": 7.99, "currency": "USD"}]

        monkeypatch.setattr(pricing.settings, "db_path", ":memory:")
        monkeypatch.setattr(pricing.settings, "discount_threshold_percent", 20.0)
        monkeypatch.setattr(pricing.db, "init_db", Mock(return_value=conn))
        monkeypatch.setattr(
            pricing.trakt,
            "get_effective_watchlist",
            Mock(
                return_value=[
                    {
                        "trakt_id": 123,
                        "media_type": "movie",
                        "title": "Broken Movie",
                        "tmdb_id": 456,
                    },
                    {
                        "trakt_id": 789,
                        "media_type": "movie",
                        "title": "Example Movie",
                        "tmdb_id": 987,
                    },
                ]
            ),
        )
        monkeypatch.setattr(pricing.justwatch, "get_amazon_prices", get_amazon_prices)
        monkeypatch.setattr(pricing.db, "get_last_price", Mock(return_value=12.99))
        monkeypatch.setattr(pricing.db, "was_notified", Mock(return_value=False))
        monkeypatch.setattr(pricing.notify, "send_alert", send_alert)
        monkeypatch.setattr(pricing.db, "log_notification", log_notification)
        monkeypatch.setattr(pricing.db, "upsert_price", upsert_price)

        pricing.check_prices()

        send_alert.assert_called_once()
        log_notification.assert_called_once_with(conn, 789, "movie", "HD", 7.99, 12.99)
        upsert_price.assert_called_once_with(conn, 789, "movie", "HD", 7.99, "USD")
        assert "Failed to process price for 123: bad justwatch response" in capsys.readouterr().err
        assert conn.closed is True
