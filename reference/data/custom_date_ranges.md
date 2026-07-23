# Custom date ranges (day-level P&L)

**Status:** BUILT 2026-07-23. The dashboard can show a P&L for any custom day range (e.g.
Feb 15 – Mar 1), in addition to the month-as-column view. Additive — `pnl_monthly` and the
reconcile/drift guards are untouched.

## The core idea

Every calculation already computes a per-transaction **attribution date**, then rounds it to a
month for `pnl_monthly`. Day-level P&L is just "keep the full date." A parallel table
`pnl_daily` holds the same numbers at day grain, and **Σ pnl_daily over a month == pnl_monthly**
by construction (both share the attribution date). A Phase-0 dry run proved this to the cent
across US/CA/UK/AU before any code was written.

## Pieces

- **`pnl_daily`** (migration `b8c9d0e1f2a3`): a date-keyed mirror of `pnl_monthly`
  (`marketplace_id, date, line_key, line_label, bucket, amount, currency`). COGS is stored
  **signed** per day (monthly `pnl_monthly.cog` is `abs()`, so the guard compares on `|Σ|`).
- **`sync/aggregate_daily.py`**: rebuilds `pnl_daily` reusing the exact production logic —
  `bucket_map.classify()`, `attribution.resolve_attribution_date` (the day-grain twin of
  `resolve_attribution_ym`, added without touching the monthly one), and the byte-for-byte COGS
  SQL with grain `::date`. `reconcile_against_monthly()` is the permanent guard.
- **Pipeline (`sync/__main__.py` Phase 4)**: runs `aggregate_daily_marketplace` after the
  monthly build, per marketplace. **Non-fatal** — a daily-build failure logs a warning and never
  blocks the reconciled monthly sync (the range view just goes stale until the next run).
- **`app/pnl.py`**: refactored so the monthly view and the range view share ONE code path —
  `_accumulate` (grid + breakdowns) and `_finalize` (rows, gross-profit, FX) run over a generic
  `periods` list. `assemble()` = months from `pnl_monthly`; `assemble_range(start, end)` = one
  period from `pnl_daily`. Each day converts at its month's FX rate; the range's FX row shows the
  day-weighted average.
- **`app/main.py`**: `GET /pnl` gained `start`/`end` (YYYY-MM-DD). Both → range view; neither →
  month view; one-without-the-other / bad date / end<start → 400.
- **Frontend**: two native `<input type="date">` + Apply/Clear. Range mode renders a single
  column headed by the range label and hides the (redundant) Total column.

## Known / accepted behaviour

- **Monthly lump-sum fees show on their posting day** (FBA storage ~the 7th, subscription ~the
  6th). A range that excludes that day shows $0 for them — accepted (no proration; owner's call).
- A **full-month range equals that month's column exactly** (verified). A partial month is the
  sum of its in-range days.
- FX for a range spanning two months is the **day-weighted average** of the two month rates.

## Refresh / ops

`pnl_daily` is rebuilt automatically by the sync pipeline (Phase 4). To rebuild + self-check
manually: `python -m sync.aggregate_daily --marketplace ALL` (exit 2 if any month fails to
reconcile to `pnl_monthly`).
