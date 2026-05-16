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
- After merging a PR, monitor the GitHub Actions run on `master` to confirm the release
  workflow succeeds (tag creation and Docker image push to GHCR). Use `gh pr checks` or
  `gh run list --branch master` to verify.
