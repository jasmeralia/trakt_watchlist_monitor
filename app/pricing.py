# Pricing evaluation logic

from typing import Any

import db
import justwatch
import notify
import trakt
from config import settings


def select_best_quality(prices: list[dict[str, Any]]) -> dict[str, Any] | None:
    """
    Given a list of price entries, return highest quality only.
    Priority: UHD > HD > SD
    """
    priority = {"UHD": 3, "HD": 2, "SD": 1}
    prices = sorted(prices, key=lambda p: priority.get(p["quality"], 0), reverse=True)
    return prices[0] if prices else None


def meets_discount_threshold(original: float, current: float, percent: float) -> bool:
    drop = (original - current) / original * 100
    return drop >= percent


def check_prices() -> None:
    conn = db.init_db(settings.db_path)
    try:
        for item in trakt.get_effective_watchlist():
            trakt_id = item.get("trakt_id")
            media_type = item.get("media_type")
            tmdb_id = item.get("tmdb_id")
            if not isinstance(trakt_id, int) or not isinstance(media_type, str):
                continue
            if not isinstance(tmdb_id, int):
                continue

            prices = justwatch.get_amazon_prices(tmdb_id, media_type)
            best_price = select_best_quality(prices)
            if best_price is None:
                continue

            quality = str(best_price["quality"])
            current_price = float(best_price["price"])
            currency = str(best_price.get("currency", "USD"))
            last_price = db.get_last_price(conn, trakt_id, media_type, quality)
            if last_price is None:
                db.upsert_price(conn, trakt_id, media_type, quality, current_price, currency)
                continue

            if current_price < last_price:
                drop_percent = (last_price - current_price) / last_price * 100
                if meets_discount_threshold(
                    last_price, current_price, settings.discount_threshold_percent
                ) and not db.was_notified(conn, trakt_id, media_type, quality, current_price):
                    title = f"Price drop: {item.get('title', 'Watchlist item')}"
                    body = (
                        f"{item.get('title', 'Watchlist item')} dropped from "
                        f"{currency} {last_price:.2f} to {currency} {current_price:.2f} "
                        f"({drop_percent:.1f}% off)."
                    )
                    notify.send_alert(title, body)
                    db.log_notification(
                        conn, trakt_id, media_type, quality, current_price, last_price
                    )
                db.upsert_price(conn, trakt_id, media_type, quality, current_price, currency)
    finally:
        conn.close()
