# Agent Development Rules

## Verification (Required on Every Code Change)

After any code change, run:

```bash
make lint-fix && make lint && make test
```

All three must pass before the task is considered complete.

## Additional Linting

- **Shell scripts** (`.sh` files): must pass `shellcheck`. Covered by `make lint` automatically.
- **Dockerfile**: must pass `hadolint`. Covered by `make lint` automatically.

## Configuration

- Never use `os.getenv` directly in application code.
- All configuration must be accessed via `from config import settings` (see `app/config.py`).
- Never commit `.env` files. Use `.env.example` as the documentation template.

## Code Style

- Python 3.12+ with strict mypy typing
- Line length: 100 characters (enforced by ruff and pylint)
- Formatting: ruff (run `make lint-fix` to auto-apply)

## Architecture Reference

See [docs/DESIGN.md](docs/DESIGN.md) for module responsibilities, SQLite schema, configuration
schema, and the discount threshold formula.

## Git Workflow

- All changes to `master` go through a pull request; direct pushes are not allowed
- PRs are squash-merged only
- The repository owner is `@jasmeralia` (see `.github/CODEOWNERS`)
- After merging a PR, immediately run `git checkout master && git pull` to bring the
  local working copy up to date before doing any further work.
- After merging a PR, check that the GitHub Actions run on `master` succeeds before
  reporting the task complete. Use `gh run list --branch master --limit 1` to get the
  run ID, then `gh run watch <id>` to wait for it, confirming the release workflow
  (tag creation and Docker image push to GHCR) completes without error.
