import time
from pricing import check_prices
from settings import settings


def main() -> None:
    while True:
        check_prices()
        time.sleep(settings.check_interval_hours * 3600)


if __name__ == "__main__":
    main()
