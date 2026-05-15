# Codex Fix Request

## Source of Truth

- `docs/DESIGN.md` — architecture, module contracts, business logic
- `docs/REVIEW.md` — full review findings with severity ratings

## Scope

Fixes identified in `docs/REVIEW.md` that require no live credentials. The JustWatch GraphQL
schema validation (which requires a real API call) is explicitly out of scope here.

## Checklist

- [x] **notify-sendmessage** `app/notify.py`: Replace `smtp.sendmail(from, to, msg.as_string())` with `smtp.send_message(msg)` — the idiomatic API for `EmailMessage`. Update `tests/test_notify.py` if the assertion on `sendmail` needs to change.

- [x] **notify-nonfatal** `app/pricing.py`: Wrap `notify.send_alert()` in a `try/except` so an SMTP failure is caught, logged to stderr, and does not abort the run. The `db.upsert_price()` call must still execute after a notification failure.

- [x] **per-item-errors** `app/pricing.py`: Wrap each item's processing block (from `justwatch.get_amazon_prices()` through the final `db.upsert_price()`) in a `try/except` that logs the error and `continue`s to the next item, so one bad item does not abort the whole run.

- [x] **upsert-on-increase** `app/pricing.py`: Move `db.upsert_price()` outside the `if current_price < last_price:` block so price increases are stored too. Only the notification logic (threshold check + `send_alert` + `log_notification`) stays inside the `if` block.

- [x] **db-tests** `tests/test_db.py`: Add two tests:
  1. Upsert the same `(trakt_id, media_type, quality)` key twice with different prices; assert `get_last_price` returns the second price (verifies ON CONFLICT REPLACE).
  2. After `log_notification` at $10.00, assert `was_notified(..., price=7.99)` returns `True` (price strictly below the logged price, verifying the `<= ?` query).

- [x] **pricing-tests** `tests/test_pricing.py`: Add four `TestCheckPrices` test cases:
  1. First observation (`get_last_price` returns `None`): assert `send_alert` is NOT called and `upsert_price` IS called.
  2. Deduplication (`was_notified` returns `True`): assert `send_alert` is NOT called even though threshold is met.
  3. No JustWatch prices (`get_amazon_prices` returns `[]`): assert `send_alert` is NOT called and `upsert_price` is NOT called.
  4. No `tmdb_id` (`tmdb_id` is `None` in the watchlist item): assert `send_alert` is NOT called and `upsert_price` is NOT called.

- [x] **trakt-session** `app/trakt.py`: Reuse a single `requests.Session` within `_request_with_refresh` (create once, use for both the initial request and the retry) instead of creating two independent sessions. Update tests if needed.

- [x] **justwatch-cleanup** `app/justwatch.py`: Remove the dead `nodes` branch from `_first_title()` since the GraphQL query only requests `edges { node { ... } }`. Add a comment to `AMAZON_PACKAGES` noting the values are unverified against the live API and may need updating.

## Constraints

- Do not touch the JustWatch GraphQL query shape or `technicalName` values — those require live API validation.
- Do not refactor unrelated code.
- All changes must pass `make lint-fix && make lint && make test`.
- Follow existing project style (typed, ruff-formatted, pylint-clean).

## Success Criteria

- All checklist items marked complete.
- `make test` passes with no regressions.
- `make lint` passes (ruff, mypy, pylint).

## Completed by Codex

- Completed `notify-sendmessage`: `send_alert` now uses `smtp.send_message(message)`, and the notify test asserts the generated `EmailMessage` content.
- Completed `notify-nonfatal`: `check_prices` now logs SMTP alert failures to stderr,
  skips notification logging when sending fails, and still upserts the observed price.
- Completed `per-item-errors`: `check_prices` now logs per-item processing failures to stderr
  and continues with later watchlist items.
- Completed `upsert-on-increase`: `check_prices` now persists observed price increases without
  sending alerts, with a pricing test covering the increase path.
- Completed `db-tests`: added database coverage for replacing an existing price on upsert,
  and aligned `was_notified` so lower prices are treated as already notified after a higher
  logged notification price.
- Completed `pricing-tests`: added `check_prices` coverage for first observations,
  deduplicated notifications, items with no JustWatch prices, and watchlist items without TMDB
  IDs.
- Completed `trakt-session`: `_request_with_refresh` now creates one `requests.Session` and
  reuses it for both the initial request and post-refresh retry, with test coverage for the
  single session factory call.
- Completed `justwatch-cleanup` on 2026-05-15: removed the unreachable `nodes` handling from
  `_first_title()` and documented that the Amazon package technical names are unverified against
  the live JustWatch API.
