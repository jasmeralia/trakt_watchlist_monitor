# Pricing evaluation logic

import logging
import smtplib
import sys
from typing import Any

import db
import justwatch
import notify
import trakt
from config import settings

logger = logging.getLogger(__name__)


def select_best_quality(prices: list[dict[str, Any]]) -> dict[str, Any] | None:
    """
    Given a list of price entries, return highest quality only.
    Priority: UHD > HD > SD
    """
    priority = {"UHD": 3, "HD": 2, "SD": 1}
    return min(
        prices,
        key=lambda p: (-priority.get(p["quality"], 0), float(p["price"])),
        default=None,
    )


def meets_discount_threshold(original: float, current: float, percent: float) -> bool:
    drop = (original - current) / original * 100
    return drop >= percent


def _new_stats() -> dict[str, int]:
    return {
        "watchlist_items": 0,
        "invalid_items": 0,
        "missing_tmdb_id": 0,
        "without_amazon_offer": 0,
        "unexpected_currency": 0,
        "first_observations": 0,
        "prices_recorded": 0,
        "alerts_sent": 0,
        "alert_failures": 0,
        "item_errors": 0,
    }


def _send_price_alert(
    item: dict[str, Any], currency: str, last_price: float, current_price: float
) -> None:
    drop_percent = (last_price - current_price) / last_price * 100
    title = f"Price drop: {item.get('title', 'Watchlist item')}"
    body = (
        f"{item.get('title', 'Watchlist item')} dropped from "
        f"{currency} {last_price:.2f} to {currency} {current_price:.2f} "
        f"({drop_percent:.1f}% off)."
    )
    notify.send_alert(title, body)


def _log_stats(stats: dict[str, int]) -> None:
    logger.info(
        "Price check complete: watchlist_items=%d invalid_items=%d missing_tmdb_id=%d "
        "without_amazon_offer=%d unexpected_currency=%d first_observations=%d "
        "prices_recorded=%d alerts_sent=%d alert_failures=%d item_errors=%d",
        stats["watchlist_items"],
        stats["invalid_items"],
        stats["missing_tmdb_id"],
        stats["without_amazon_offer"],
        stats["unexpected_currency"],
        stats["first_observations"],
        stats["prices_recorded"],
        stats["alerts_sent"],
        stats["alert_failures"],
        stats["item_errors"],
    )


def _extract_item_fields(
    item: dict[str, Any], stats: dict[str, int]
) -> tuple[int, str, int] | None:
    trakt_id = item.get("trakt_id")
    media_type = item.get("media_type")
    tmdb_id = item.get("tmdb_id")
    if not isinstance(trakt_id, int) or not isinstance(media_type, str):
        stats["invalid_items"] += 1
        return None
    if not isinstance(tmdb_id, int):
        stats["missing_tmdb_id"] += 1
        return None
    return trakt_id, media_type, tmdb_id


def check_prices() -> None:
    conn = db.init_db(settings.db_path)
    stats = _new_stats()
    logger.info("Checking watchlist prices")
    # pylint: disable=too-many-nested-blocks
    try:
        watchlist = trakt.get_effective_watchlist()
        stats["watchlist_items"] = len(watchlist)
        for item in watchlist:
            item_fields = _extract_item_fields(item, stats)
            if item_fields is None:
                continue
            trakt_id, media_type, tmdb_id = item_fields

            try:
                best_price = select_best_quality(justwatch.get_amazon_prices(tmdb_id, media_type))
                if best_price is None:
                    stats["without_amazon_offer"] += 1
                    continue

                quality = str(best_price["quality"])
                current_price = float(best_price["price"])
                currency = str(best_price.get("currency", "USD"))
                if currency != "USD":
                    stats["unexpected_currency"] += 1
                    print(
                        f"Unexpected currency {currency!r} for trakt_id {trakt_id}; skipping",
                        file=sys.stderr,
                    )
                    continue
                last_price = db.get_last_price(conn, trakt_id, media_type, quality)
                if last_price is None:
                    stats["first_observations"] += 1
                    stats["prices_recorded"] += 1
                    db.upsert_price(conn, trakt_id, media_type, quality, current_price, currency)
                    continue

                if last_price != 0.0 and current_price < last_price:
                    if meets_discount_threshold(
                        last_price, current_price, settings.discount_threshold_percent
                    ) and not db.was_notified(conn, trakt_id, media_type, quality, current_price):
                        try:
                            _send_price_alert(item, currency, last_price, current_price)
                        except (OSError, smtplib.SMTPException) as exc:
                            stats["alert_failures"] += 1
                            print(
                                f"Failed to send price alert for {trakt_id}: {exc}",
                                file=sys.stderr,
                            )
                            continue
                        else:
                            stats["alerts_sent"] += 1
                            db.log_notification(
                                conn, trakt_id, media_type, quality, current_price, last_price
                            )
                stats["prices_recorded"] += 1
                db.upsert_price(conn, trakt_id, media_type, quality, current_price, currency)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                stats["item_errors"] += 1
                print(f"Failed to process price for {trakt_id}: {exc}", file=sys.stderr)
                continue
    finally:
        conn.close()
    _log_stats(stats)
