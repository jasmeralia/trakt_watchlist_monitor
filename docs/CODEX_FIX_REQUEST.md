# Codex Fix Request — Adversarial Review

## Source of Truth

- `docs/DESIGN.md` — architecture and module contracts
- `docs/ADVERSARIAL_REVIEW.md` — full adversarial review findings

## Scope

Fixes for findings that have a clear correct answer and do not require config schema
changes or DB migrations. Items that require design decisions (token persistence,
currency key, SMTP_SSL, season support) are explicitly out of scope here.

## Checklist

- [x] **main-loop-resilience** `app/main.py`: Wrap the body of the `while True` loop in a
  `try/except Exception` that logs the error to stderr and sleeps before retrying, so a
  transient Trakt failure or DB open error does not kill the service permanently.

- [x] **smtp-timeout** `app/notify.py`: Pass a `timeout` argument (e.g. `30`) to
  `smtplib.SMTP()` so a stalled server cannot block the monitoring loop indefinitely.

- [x] **graphql-errors** `app/justwatch.py`: After `response.raise_for_status()`, inspect
  the parsed JSON for a top-level `"errors"` key. If present, log the first error message
  to stderr and return `[]` rather than silently falling through as if no offers were found.

- [x] **price-parse-locale** `app/justwatch.py`: Fix `_parse_price()` so that
  comma-decimal strings like `"€9,99"` and thousands-separator strings like `"1,299.00"`
  do not produce bogus numbers. The correct approach: strip all non-digit, non-period, and
  non-comma characters, replace any comma that acts as a decimal separator (rightmost
  comma followed by exactly two digits at end of string) with a period, then remove
  remaining commas, and parse the result. Add tests for both formats.

- [ ] **zero-division-guard** `app/pricing.py`: Guard against `last_price == 0.0` in the
  discount-percentage calculation inside `check_prices()`. If `last_price` is zero, skip
  the notification logic (a zero baseline is not a meaningful reference price) and still
  call `upsert_price`.

- [ ] **upsert-after-alert** `app/pricing.py` + `tests/test_pricing.py`: The critical bug:
  when the threshold is met and alert sending fails, `upsert_price` still runs, permanently
  preventing future re-alerts. Fix: only call `upsert_price` when the alert was either
  (a) sent successfully, or (b) not required (below threshold, first observation, price
  increase). When an alert was required but the send failed, skip `upsert_price` so the
  next run retries. Update the notify-failure test to assert that `upsert_price` is NOT
  called when send fails.

- [ ] **season-log** `app/trakt.py`: In `_normalize_watchlist_item()`, add an explicit
  `elif item["type"] not in {"movie", "show"}` branch that logs the unsupported type to
  stderr and returns `None`, rather than falling through silently.

- [ ] **select-cheapest-quality** `app/pricing.py` `select_best_quality()`: When multiple
  offers share the same quality tier, select the one with the lowest price rather than the
  first encountered. Update or add a test for this case.

## Constraints

- Do not add new config fields or modify pydantic Settings.
- Do not change the DB schema or add migrations.
- Do not add SMTP_SSL support (out of scope).
- Do not implement season lookup via JustWatch (out of scope).
- All changes must pass `make lint-fix && make lint && make test`.
- Follow existing project style (typed, ruff-formatted, pylint-clean).

## Success Criteria

- All checklist items marked complete.
- `make test` passes with no regressions.
- `make lint` passes (ruff, mypy, pylint).

## Completed by Codex

- Completed `main-loop-resilience` on 2026-05-15: `main()` now catches and logs unexpected
  loop failures with traceback details, then waits the configured interval before retrying.
- Completed `smtp-timeout` on 2026-05-15: SMTP alert delivery now uses a 30-second
  connection timeout.
