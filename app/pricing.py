# Pricing evaluation logic

from typing import Any


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
    # TODO: Pull effective watchlist, lookup prices, compare history
    pass
