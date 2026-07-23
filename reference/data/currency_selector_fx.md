# Currency selector + monthly FX (CA/UK/AU native ↔ USD)

**Status:** BUILT (2026-07-23). Applies to the v1 P&L dashboard. Display-layer only; extraction /
`pnl_monthly` / reconcile untouched.

## Implemented

- **`fx_monthly_rates` table** (migration `a7b8c9d0e1f2`): one row per (currency, year_month) =
  native→USD, the monthly average of a daily feed. `sync/fx_rates.py` pulls it.
- **`sync.fx_rates`** pulls daily rates from **Frankfurter (ECB)** — tracks Google closely, since a
  clean Google API doesn't exist — inverts USD→native to native→USD, averages per month, upserts.
  Run: `python -m sync.fx_rates --start 2026-01-01 --end 2026-06-30`. Offline/cron step; the API reads
  the table, never the network per request.
- **`app/pnl.py`**: `_convert` now takes the month + a rates map loaded from `fx_monthly_rates`
  (`_load_monthly_rates`); a missing (currency, month) falls back to `BOOK_RATES_TO_USD`. `assemble`
  gained `view_currency`; the response carries `native_currency`.
- **`app/main.py`**: `GET /pnl` gained `currency=native|usd` (400 on anything else). US/ALL always USD.
- **Frontend**: a native↔USD toggle (segmented control) shown only for CA/UK/AU; subtitle notes
  "converted at monthly avg rate" on any USD-converted view.
- **Realized rates (Jan–Jun 2026 avg):** CAD ~0.726 (book 0.71), GBP ~1.346 (1.34), AUD ~0.702 (0.69).
  Verified: ALL Sales shifted 960,893→962,891; CA/UK/AU USD views tie to native × the monthly rate;
  UK native unchanged (cog is GBP); all breakdown partitions still hold (ALL within ~2¢ rounding).

### Resolved decisions (were open)

1. Rate source → **auto-pulled** Frankfurter/ECB (Google-adjacent), month-averaged.
2. Basis → **month-average** of daily rates.
3. Fallback → **book rate** for any unconfigured (currency, month).
4. The ALL + CA/AU-native-cog shift vs book rates is accepted (more accurate).

---

_Original design record below._

## Decision

Add a **native ↔ USD** toggle for the non-USD marketplaces (CA, UK, AU). The USD conversion uses a
**per-month rate per currency (Tier 2)**, sourced from **Google's daily FX rate aggregated to one rate
per month**. This replaces the single fixed book rate on the USD path.

Confirmed by the owner: the realized rate the business uses *is* Google's daily rate, and a fixed
monthly rate is acceptable.

## Why monthly, not daily (Tier 3 rejected)

- `pnl_monthly` stores only **monthly** native sums — no per-day P&L amounts are retained
  (`sales_daily` is empty; only `ad_spend_daily` is daily). A true daily-rate USD figure would require
  re-aggregating from `sp_transactions.posted_at` at each day's rate, and most fee/COGS lines are
  monthly-only regardless. A per-month rate is the exact granularity match.

## Data facts (verified 2026-07-23)

- Amazon stores CA/UK/AU amounts **native only** (CAD/GBP/AUD) across `sp_transactions`,
  `sp_breakdowns`, `pnl_monthly`. Raw transaction JSON has **no `exchangeRate` / no USD leg**; the
  `FundTransfer` disbursement is native (conversion happens at the bank, invisible to us).
- **No FX/rate table exists** in the DB. The only rate today is `BOOK_RATES_TO_USD` in `pnl.py`
  (fixed: GBP 1.34, CAD 0.71, AUD 0.69).
- `cog` is stored **USD for CA & AU** (MARKETPLACE_COG_SOURCE_OVERRIDE), **GBP for UK**, USD for US.
- Reconcile's own AU implied rate (~0.67) already differs from the book 0.69 (~3%) — evidence the
  static book rate drifts from the realized rate.

## Design

- Replace `BOOK_RATES_TO_USD` (single dict) with `MONTHLY_RATES[ym][ccy]` (native→USD per month).
- Thread the month into `_convert(amount, src, dst, ym)`; the USD-pivot formula is unchanged:
  `amount * rate[ym][src] / rate[ym][dst]`. All call sites already have `ym` in scope.
- Toggle: CA/UK/AU → native **or** USD; US always USD; ALL always USD (now at monthly rates).
- The "convert by each value's own currency" rule is preserved, so CA/AU `cog` (USD) converts
  USD→native at that month's rate — the double-conversion trap stays structurally impossible.

## Impacts — this shifts some already-shipped numbers

| View | Effect of book→monthly rates |
|---|---|
| **ALL** (USD) | numbers change (more accurate); Gross Profit ALL shifts |
| **CA / AU native** | `cog` is USD-sourced → native `cog` (and Profit) shifts ~1–3% per month |
| **UK native** | `cog` is native GBP → **unaffected** |
| **US** | all USD → **unaffected** |

## Open items (blockers before build)

1. **Monthly rate numbers** — a `month → {CAD, GBP, AUD}` table (native→USD), Jan–Jun 2026 minimum
   (ideally every month in `pnl_monthly` + ongoing). DMS provides from Google, **or** we auto-pull a
   Google-adjacent feed (ECB/Frankfurter) and average — the latter may diverge slightly from Google.
2. **Aggregation basis** — month-average of Google's daily rate (recommended) vs month-end vs a
   specific day.
3. **Fallback** for a month with no configured rate — hard error vs book-rate fallback.
4. Confirm acceptance of the ALL + CA/AU-native-cog shift vs the current book-rate figures.
