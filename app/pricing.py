# Pricing evaluation logic

def select_best_quality(prices):
    """
    Given a list of price entries, return highest quality only.
    Priority: UHD > HD > SD
    """
    priority = {"UHD": 3, "HD": 2, "SD": 1}
    prices = sorted(
        prices,
        key=lambda p: priority.get(p["quality"], 0),
        reverse=True
    )
    return prices[0] if prices else None

def meets_discount_threshold(original, current, percent):
    drop = (original - current) / original * 100
    return drop >= percent

def check_prices():
    # TODO: Pull effective watchlist, lookup prices, compare history
    pass
