import logging
import time
from pathlib import Path

import db
from config import settings
from pricing import check_prices

logger = logging.getLogger(__name__)


def _maybe_reset_alerts() -> None:
    flag_path = Path(settings.db_path).parent / "reset_alerts"
    if not flag_path.exists():
        return
    flag_path.unlink()
    conn = db.init_db(settings.db_path)
    try:
        counts = db.reset_notification_state(conn)
    finally:
        conn.close()
    logger.info(
        "Alert state reset: %d price(s) restored, %d first-observation price(s) cleared, "
        "%d notification(s) removed.",
        counts["prices_restored"],
        counts["prices_cleared"],
        counts["notifications_cleared"],
    )


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    while True:
        try:
            logger.info("Starting monitoring cycle")
            _maybe_reset_alerts()
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
