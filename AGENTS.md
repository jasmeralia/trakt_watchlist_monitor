# Agent Instructions

This repo checks Trakt watchlists for price changes and sends notifications.

## After Any Code Change

```bash
make lint-fix && make lint
```

Resolve all reported issues before committing.

## Git Workflow

- Never push commits directly to `master`. Always open a pull request from a feature/fix branch.
- Use squash merge strategy when merging pull requests.

## Key Files

- `app/main.py` — entry point, polling loop
- `app/pricing.py` — price check logic
- `app/settings.py` — pydantic-settings configuration (reads `.env` / `/app/.env`)

## Runtime

- Runs as a Docker container.
- Configure via environment variables or bind-mounted `/app/.env`.
