# Prime Trakt Monitor

Monitors a Trakt watchlist (movies and shows/seasons), excludes collected items,
checks Amazon Prime Video *buy* prices via JustWatch metadata, and sends email
notifications when prices drop below a **percentage-based threshold**.

## Features
- Trakt Watchlist + Collection as source of truth
- Amazon Prime Video only
- Percentage-based discount thresholds
- Highest quality pricing only (UHD > HD > SD)
- Dockerized, SMTP notifications (Gmail supported)

## Status
Initial draft – logic skeleton and structure only.
