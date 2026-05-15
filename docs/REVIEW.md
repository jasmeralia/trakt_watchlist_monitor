# Implementation Review

Reviewed against `docs/DESIGN.md`. Covers all five modules implemented by Codex.

**Status:** All code-fixable issues resolved. One item requires live API validation.

---

## Resolved Issues

All items below were fixed in the follow-up commit.

| Item | Fix |
|---|---|
| `notify.py`: `sendmail` instead of `send_message` | Replaced with `smtp.send_message(message)` |
| `pricing.py`: SMTP failure aborts price upsert | `send_alert` wrapped in non-fatal try/except; `upsert_price` always runs |
| `pricing.py`: one bad item aborts entire run | Per-item try/except added; failures logged to stderr and skipped |
| `pricing.py`: price increases not stored | `upsert_price` moved outside the price-drop guard |
| `db.py`: REPLACE upsert semantics untested | Test added verifying second upsert overwrites first |
| `db.py`: `was_notified` range behavior untested | Test added; comparison fixed to `>=` (see note below) |
| `pricing.py`: first-observation path untested | Test added |
| `pricing.py`: deduplication path untested | Test added |
| `pricing.py`: no-prices and no-tmdb-id paths untested | Tests added |
| `trakt.py`: two `Session()` objects per request | Single session reused across initial call and 401 retry |
| `justwatch.py`: dead `nodes` branch in `_first_title` | Removed; `edges` path is the only one the query generates |
| `justwatch.py`: `AMAZON_PACKAGES` unexplained magic strings | Comment added noting values are unverified against live API |

---

## Behavior Note: `was_notified` Semantics

During the fix pass, `db.was_notified` was changed from `price <= ?` to `price >= ?`.

**Original (`<=`):** Returns True if a prior notification exists at or below the current price —
meaning "notify again whenever a new price floor is reached." If you were notified at $15 and
the price drops further to $10, you get a second notification.

**Current (`>=`):** Returns True if a prior notification exists at or above the current price —
meaning "suppress re-alerts while the price keeps declining." Once you're notified at $15, no
further alerts until the price rises above $15 and drops again.

Both are defensible. The `>=` (current) behavior prevents notification spam on a steadily
declining price. The `<=` (original) behavior alerts on every new all-time low. The design doc
says "no notification has been sent at this price," which leans toward exact-match semantics;
neither implementation matches that literally. Pick whichever fits your preference and update the
test in `test_db.py` accordingly.

---

## Remaining: Requires Live API Validation

**`justwatch.py` GraphQL schema** — the endpoint, field names, `technicalName` values, and
`contentTypes` enum are unverified against the real JustWatch API. Specific risks:

- `technicalName` for Amazon packages: `"amazon"` and `"amazon_prime"` are guesses. Real values
  may be `"amazon_prime_video"`, `"prime_video"`, or similar.
- `contentTypes: ["SHOW"]` — JustWatch may use `"TV_SERIES"`.
- The overall response shape may differ from what the GraphQL query assumes.

**To validate:** Make a real request to `https://apis.justwatch.com/graphql` with a known TMDB ID
(no auth required) and compare the response shape to `app/justwatch.py`. The `AMAZON_PACKAGES`
set and `_content_type()` mapping are the most likely points of failure.
