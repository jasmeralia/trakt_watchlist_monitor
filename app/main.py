import logging
import time

from config import settings
from pricing import check_prices

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    while True:
        try:
            logger.info("Starting monitoring cycle")
            check_prices()
            logger.info(
                "Monitoring cycle complete; sleeping for %.2f hours",
                settings.check_interval_hours,
            )
            time.sleep(settings.check_interval_hours * 3600)
        except Exception:  # pylint: disable=broad-exception-caught
            logging.exception("Monitoring loop failed")
            time.sleep(settings.check_interval_hours * 3600)


if __name__ == "__main__":
    main()
