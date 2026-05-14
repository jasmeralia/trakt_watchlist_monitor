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

## Using a .env file

Rather than embedding credentials in your `docker-compose.yml`, you can store them in a `.env` file and bind-mount it into the container:

```bash
cp .env.example .env
# edit .env with your values
```

```yaml
services:
  app:
    image: ghcr.io/jasmeralia/trakt_watchlist_monitor:latest
    volumes:
      - /path/to/your/.env:/app/.env:ro
```

The app loads `/app/.env` automatically on startup. Any value in `.env` can still be overridden by an explicit `environment:` entry in your Compose file.