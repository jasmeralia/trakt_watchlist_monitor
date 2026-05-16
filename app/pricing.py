# Pricing evaluation logic

import logging
import smtplib
import sqlite3
import sys
from dataclasses import dataclass
from typing import Any

import db
import justwatch
import notify
import trakt
from config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PriceDrop:
    item: dict[str, Any]
    trakt_id: int
    media_type: str
    quality: str
    current_price: float
    currency: str
    last_price: float


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


def _format_prices(prices: list[dict[str, Any]]) -> str:
    if not prices:
        return "[]"
    return "[" + ", ".join(_format_price(price) for price in prices) + "]"


def _format_price(price: dict[str, Any]) -> str:
    return (
        f"quality={price.get('quality')!r} "
        f"price={price.get('price')!r} "
        f"currency={price.get('currency')!r}"
    )


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


def _process_watchlist_item(
    conn: sqlite3.Connection,
    item: dict[str, Any],
    item_fields: tuple[int, str, int],
    stats: dict[str, int],
) -> None:
    trakt_id, media_type, tmdb_id = item_fields
    logger.debug(
        "Polling watchlist item: trakt_id=%d media_type=%s tmdb_id=%d title=%r",
        trakt_id,
        media_type,
        tmdb_id,
        item.get("title", ""),
    )

    prices = justwatch.get_amazon_prices(tmdb_id, media_type)
    logger.debug(
        "Prices seen for trakt_id=%d media_type=%s tmdb_id=%d: offer_count=%d offers=%s",
        trakt_id,
        media_type,
        tmdb_id,
        len(prices),
        _format_prices(prices),
    )

    best_price = select_best_quality(prices)
    if best_price is None:
        stats["without_amazon_offer"] += 1
        logger.debug("No Amazon buy offer found for trakt_id=%d", trakt_id)
        return

    quality = str(best_price["quality"])
    current_price = float(best_price["price"])
    currency = str(best_price.get("currency", "USD"))
    logger.debug(
        "Selected best price for trakt_id=%d: quality=%s price=%.2f currency=%s",
        trakt_id,
        quality,
        current_price,
        currency,
    )
    if currency != "USD":
        stats["unexpected_currency"] += 1
        print(
            f"Unexpected currency {currency!r} for trakt_id {trakt_id}; skipping",
            file=sys.stderr,
        )
        return

    last_price = db.get_last_price(conn, trakt_id, media_type, quality)
    logger.debug(
        "Stored price for trakt_id=%d media_type=%s quality=%s: last_price=%r",
        trakt_id,
        media_type,
        quality,
        last_price,
    )
    if last_price is None:
        stats["first_observations"] += 1
        stats["prices_recorded"] += 1
        logger.debug("Recording first observed price for trakt_id=%d", trakt_id)
        db.upsert_price(conn, trakt_id, media_type, quality, current_price, currency)
        return

    if last_price != 0.0 and current_price < last_price:
        price_drop = PriceDrop(
            item=item,
            trakt_id=trakt_id,
            media_type=media_type,
            quality=quality,
            current_price=current_price,
            currency=currency,
            last_price=last_price,
        )
        should_record_price = _handle_price_drop(conn, price_drop, stats)
        if not should_record_price:
            return
    else:
        logger.debug(
            "No qualifying price drop for trakt_id=%d: last_price=%.2f current_price=%.2f",
            trakt_id,
            last_price,
            current_price,
        )

    stats["prices_recorded"] += 1
    db.upsert_price(conn, trakt_id, media_type, quality, current_price, currency)


def _handle_price_drop(
    conn: sqlite3.Connection,
    price_drop: PriceDrop,
    stats: dict[str, int],
) -> bool:
    drop_percent = (price_drop.last_price - price_drop.current_price) / price_drop.last_price * 100
    logger.debug(
        "Price drop seen for trakt_id=%d: last_price=%.2f current_price=%.2f drop_percent=%.1f",
        price_drop.trakt_id,
        price_drop.last_price,
        price_drop.current_price,
        drop_percent,
    )
    if not meets_discount_threshold(
        price_drop.last_price,
        price_drop.current_price,
        settings.discount_threshold_percent,
    ):
        logger.debug(
            "Price drop below threshold for trakt_id=%d: threshold_percent=%.1f",
            price_drop.trakt_id,
            settings.discount_threshold_percent,
        )
        return True
    if db.was_notified(
        conn,
        price_drop.trakt_id,
        price_drop.media_type,
        price_drop.quality,
        price_drop.current_price,
    ):
        logger.debug(
            "Skipping duplicate alert for trakt_id=%d price=%.2f",
            price_drop.trakt_id,
            price_drop.current_price,
        )
        return True

    try:
        _send_price_alert(
            price_drop.item,
            price_drop.currency,
            price_drop.last_price,
            price_drop.current_price,
        )
    except (OSError, smtplib.SMTPException) as exc:
        stats["alert_failures"] += 1
        print(
            f"Failed to send price alert for {price_drop.trakt_id}: {exc}",
            file=sys.stderr,
        )
        return False
    stats["alerts_sent"] += 1
    db.log_notification(
        conn,
        price_drop.trakt_id,
        price_drop.media_type,
        price_drop.quality,
        price_drop.current_price,
        price_drop.last_price,
    )
    return True


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

            try:
                _process_watchlist_item(conn, item, item_fields, stats)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                stats["item_errors"] += 1
                trakt_id = item_fields[0]
                print(f"Failed to process price for {trakt_id}: {exc}", file=sys.stderr)
                continue
    finally:
        conn.close()
    _log_stats(stats)
