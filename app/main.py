import time
from pricing import check_prices

INTERVAL_HOURS = int(float(
    __import__("os").getenv("CHECK_INTERVAL_HOURS", "24")
))

def main():
    while True:
        check_prices()
        time.sleep(INTERVAL_HOURS * 3600)

if __name__ == "__main__":
    main()
