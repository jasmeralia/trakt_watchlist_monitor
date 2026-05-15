# Implementation Review

Reviewed against `docs/DESIGN.md`. Covers all five modules implemented by Codex.
22 tests pass; pylint 10.00/10; ruff and mypy clean.

---

## Overall Assessment

The core pipeline is functionally correct end-to-end. The design doc is faithfully followed in
terms of module structure, function signatures, SQLite schema, and the discount/deduplication
logic. However, there are several gaps in resilience, one likely-broken JustWatch GraphQL
integration, and missing test cases for edge paths the design calls out explicitly.

---

## app/db.py

**Conformance: ✅ Matches design.**

Schema matches exactly. All five required functions are present and typed.

The `upsert_price` INSERT relies on the table-level `ON CONFLICT REPLACE` clause to handle
duplicates — correct and clean. The `was_notified` query uses `price <= ?`, which suppresses
duplicate alerts for any price at or below a previously notified price; this is stricter than
"at this price" but aligns with the design intent.

**Issues:**

- The `REPLACE` upsert semantics are not tested. The existing test only verifies insert-then-read.
  A second upsert at a different price for the same key should replace the row — this case is
  untested and important for correctness.

- `was_notified` at a price strictly below a logged price is not tested. The query is `price <= ?`,
  so notifying at $10 should block a subsequent notification at $7 — no test covers this.

---

## app/notify.py

**Conformance: ✅ Matches design.**

STARTTLS on port 587, `EmailMessage`, plain-text body, correct settings fields used.

**Issues:**

- **No error handling.** If the SMTP connection fails (wrong credentials, server unreachable,
  TLS error), the exception propagates through `check_prices()` and aborts the entire run —
  including the `db.upsert_price()` call that should still happen regardless of notification
  success. A notification failure should be logged and swallowed, not fatal.

- Uses `smtp.sendmail(from, to, message.as_string())` instead of `smtp.send_message(message)`.
  Both work, but `send_message` is the idiomatic API for `EmailMessage` and avoids manually
  serialising headers that the `EmailMessage` object already encodes.

- The test only covers the happy path. No tests for SMTP auth failure or connection error.

---

## app/trakt.py

**Conformance: ✅ Matches design.**

All required functions present and typed. 401 refresh-and-retry implemented correctly.
`get_effective_watchlist()` returns the normalized shape the design specifies.

**Issues:**

- **`_request_with_refresh` creates a new `requests.Session()` on every call** — two sessions
  per request (one initial, one retry), with no connection pooling. Not broken, but a single
  module-level or function-scoped session would be more efficient and easier to mock.

- The 401 retry does not cap retries at the function level — if `refresh_token()` itself fails
  (e.g., network error or bad refresh token), an exception propagates up uncaught and aborts
  the run. No retry guard or error handling around the refresh call.

- `_item_trakt_id` (used to build `collection_ids`) returns `int | None`. The resulting set
  can contain `None`. This is harmless because `_normalize_watchlist_item` only produces items
  with `int` trakt IDs, but it's an unnecessary type widening.

- No tests for: malformed watchlist items (missing `type`), watchlist items without a `tmdb_id`,
  or network-level exceptions.

---

## app/justwatch.py

**Conformance: ⚠️ Structurally matches design; GraphQL schema is unverified.**

The function signature, return shape, Amazon filtering, and quality normalization all match.
The `4K` → `UHD` mapping is present. The dual `nodes`/`edges` fallback is pragmatic.

**Issues:**

- **`_first_title` has dead code.** The GraphQL query only requests `edges { node { ... } }`,
  so `nodes` will never appear in the response. The `nodes` branch in `_first_title` will
  never execute. The `edges` path is the only one that runs.

- **GraphQL schema is unverified against the live API.** JustWatch has no publicly documented
  GraphQL contract. Specific risks:
  - `searchTitles(externalIds: {tmdb: ...})` — field name and argument shape may differ.
  - `technicalName` values for Amazon packages: `"amazon"` and `"amazon_prime"` are guesses.
    The real values might be `"amazon_prime_video"`, `"prime_video"`, or similar.
  - `contentTypes: ["SHOW"]` — JustWatch may use `"TV_SERIES"` for TV content.
  - `presentationType` values: `"4K"` and `"UHD"` are handled, but actual values returned
    need verification against a live response.

  This module requires end-to-end testing against the real API before the service can be
  considered functional.

- **`AMAZON_PACKAGES` is a module-level set with magic strings.** Should be a named constant
  with a comment explaining where these names come from and noting they may need updating.

- No test for the `4K` → `UHD` quality mapping path.
- No test for `show` media type (only `movie` is tested).

---

## app/pricing.py — `check_prices()`

**Conformance: ✅ Matches design flow exactly.**

All six steps of the design's orchestration flow are implemented correctly and in order.
The `try/finally` ensures the DB connection is always closed. Price drop percentage uses
`last_price` as the denominator, consistent with the design formula.

**Issues:**

- **No per-item exception handling.** If `justwatch.get_amazon_prices()` raises (network error,
  API change, unexpected response shape), the exception propagates out of the `for` loop,
  through `check_prices()`, and up to `main()`. The entire run fails; all remaining watchlist
  items are skipped. Each item's processing should be wrapped in `try/except` so one bad item
  does not abort the run.

- **Same issue for `trakt.get_effective_watchlist()`.** A Trakt API failure aborts the full
  run. This should be caught at the call site or in `main()` with appropriate logging.

- **Price increases are silently ignored.** `db.upsert_price` is only called inside the
  `if current_price < last_price:` block. If a price rises (e.g., $10 → $15), the DB is not
  updated. The stored price remains the old lower value. On the next run, the comparison is
  against the stale low price, potentially suppressing a future genuine discount. This is
  consistent with the design doc's flow description but is a meaningful behavioral gap worth
  revisiting.

- **Missing test cases for explicitly designed paths:**
  - First observation (no `last_price`): should upsert and not alert. Not tested.
  - `was_notified=True` (deduplication): should upsert but not alert. Not tested.
  - Item with no JustWatch prices: should skip silently. Not tested.
  - Item with `tmdb_id=None`: should skip silently. Not tested.

---

## Summary of Issues

| Severity | Module | Issue |
|---|---|---|
| High | `notify.py` | SMTP exceptions abort price upsert; notification failures should be non-fatal |
| High | `pricing.py` | No per-item exception handling; one bad item aborts the whole run |
| High | `justwatch.py` | GraphQL schema is unverified; `technicalName` values and field names may be wrong |
| Medium | `pricing.py` | Price increases not stored; DB holds stale low price after a rise |
| Medium | `pricing.py` | No tests for first-observation, deduplication, no-prices, and no-tmdb-id paths |
| Medium | `db.py` | REPLACE upsert semantics not tested; `was_notified` range behavior not tested |
| Low | `trakt.py` | New `Session()` on every call; no connection pooling |
| Low | `justwatch.py` | `_first_title` nodes-path is dead code given the query structure |
| Low | `notify.py` | `sendmail` instead of `send_message` for `EmailMessage` |
| Low | `justwatch.py` | `AMAZON_PACKAGES` magic strings need a comment explaining provenance |

---

## Recommended Next Steps

1. **Validate `justwatch.py` against the live API** before anything else — the GraphQL schema,
   package technical names, and content type values are unverified guesses. This is the highest
   integration risk in the entire implementation.

2. **Add per-item error handling in `check_prices()`** so a single item failure is logged and
   skipped rather than aborting the run.

3. **Make `send_alert` non-fatal** — catch exceptions, log them, and allow `check_prices()` to
   continue with the price upsert regardless.

4. **Fill the test gaps** in `pricing.py` for the first-observation, deduplication,
   no-prices, and no-tmdb-id paths.
