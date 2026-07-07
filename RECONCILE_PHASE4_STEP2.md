# Claude Code Task — Phase 4 Step 2: monthly Ads pull → persist → wire into net

## Context

Step 1 probe resolved every structural question against real data, and the residual diagnosis
concluded the sub-dollar month deltas are **post-snapshot restatement drift** (Amazon revises
Ads report data after the fact; Sellerise's snapshot and our fresh pull differ where Amazon has
since revised). That verdict shapes this build. Everything below is settled from Step 1:

- Header: `Amazon-Ads-ClientId`.
- US `advertiserAccountId`: `amzn1.ads-account.g.a86z4ip0byyr0754l34817zfs`.
- `metric.totalCost` **requires** `budgetCurrency.value`; filter `budgetCurrency = USD`
  (account also has CAD/AUD/GBP campaigns).
- Query must include a level-of-detail dimension: include `campaign.id`.
- `adProduct.value` returns only `Sponsored Products` / `Sponsored Brands` / `Sponsored Display`
  — **no SB Video, no SB TV**. Merge `hsaCost + hsaVideoCost` into the `SPONSORED_BRANDS` line;
  `stvCost` is 0/absent.
- `metric.totalCost` is in **currency units**, not micros.
- `POST /adsApi/v1/retrieve/reports` accepts **one `reportId` per request** (400000 on a list,
  despite the docs example) — poll one report per call.

Goal: pull Jan 2026 → now, persist daily ad spend, and subtract `adExpenses` into net to close
the ~$18k/month gap. US only.

## Operating rules

- Minimalist: a pull + persist + a subtraction into net. No new dependencies. Reuse the Step 1
  report client.
- Measure before/after and report numbers; don't widen tolerance to force closure.
- Reconcile the ad lines against Sellerise **first**; wire into net only after they match.

## Three things this build MUST carry (from the restatement diagnosis)

1. **Persist an as-of timestamp per row.** Because restatement means the same month returns
   slightly different `totalCost` on different pull dates, `ad_spend_daily` is a snapshot, not
   fixed truth. Store the pull/as-of datetime alongside every row. Without it, you cannot later
   tell restatement (expected sub-dollar drift) from a real pipeline change (a bug) — the
   timestamp is what makes that distinguishable.
2. **Mark the trailing month(s) as EXPECTED-to-drift, not FAIL.** A month Amazon is still
   restating is an in-flight number, exactly like the P&L side's trailing `DEFERRED`. Settled
   (older) months reconcile confidently; the current month's ad lines are expected to move.
3. **`retrieve/reports` is one `reportId` per call.** The polling loop calls it once per report.
   If you create multiple reports (per month or per period chunk), poll each independently at
   ~1/min. Do not batch reportIds.

## Step 2a — Pull

- Fields: `date.value`, `adProduct.value`, `campaign.id`, `budgetCurrency.value`,
  `metric.totalCost`. Filter/keep `budgetCurrency = USD`.
- Range: Jan 1 2026 → now. Run create → poll (one reportId/call, ~1/min) → retrieve →
  download `completedReportParts` (handle `PARTITIONED_*` if large). Handle
  `PENDING`/`PROCESSING`/`COMPLETED`/`FAILED`.
- **Verify the create-side rate/concurrency limit empirically** (like everything else) before
  parallelizing report creation — don't assume how many reports you can have in flight.

## Step 2b — Persist

- Table `ad_spend_daily`, keyed by `(date, adProduct, campaign_id)` in USD, with `total_cost`
  and an **`as_of` pull timestamp**. Aggregate to `{month, adProduct}` for reconciliation, with
  SB Video merged into SB.
- Make the pull resumable (reuse the Orders sweep's `sync_state` pattern) and idempotent —
  re-running a month replaces that month's rows and updates `as_of`, rather than duplicating.

## Step 2c — Reconcile the ad lines, then wire into net

- **First**, reconcile per month (Jan–Jun) against Sellerise's ad lines in
  `SELLERISE_RAW_DATA.json`: four lines (SP, SB-merged, SD, STV) + total, ours vs Sellerise vs
  delta. Apply a **per-line sub-dollar tolerance with a note** so restatement drift
  (e.g. SP Feb −$1.46, SB Jan −$0.60, SB Apr +$3.06) shows as PASS-with-note, not FAIL.
- **Only once** total monthly spend matches Sellerise within tolerance for settled months,
  subtract `adExpenses` into net in `reconcile.py` and re-run the full report.
- Emit **net before/after** per month: net gap with `adExpenses=0` vs with real spend, vs
  Sellerise. Confirm the ~$18k/month closes for settled months. If a residual remains, report it
  by line — don't assume it's the ad total.

## Guardrails / accepted residuals

- Sub-dollar restatement drifts are accepted and labeled as such — never chased, never widened
  into by loosening tolerance beyond the sub-dollar band.
- The trailing month's ad lines are EXPECTED-to-drift; do not mark them FAIL.
- SB Video stays merged into SB (API can't split it) — documented, not forced.
- Leave the P&L-side decisions (A–G, status split, purchase-date attribution, unsourceable
  appendix) untouched.

## Definition of done

- Jan→now USD ad spend pulled and persisted to `ad_spend_daily` with a per-row `as_of`
  timestamp; pull is resumable and idempotent.
- Ad lines reconciled vs Sellerise: settled months within the sub-dollar per-line tolerance
  (drift shown as PASS-with-note); trailing month marked EXPECTED-to-drift.
- `adExpenses` wired into net; report re-run; the ~$18k/month net gap closed for settled months
  (or residual explained by line).
- `retrieve/reports` polled one reportId per call; create-side concurrency limit verified
  empirically and recorded.
- Restatement handling (as-of timestamp, trailing-month EXPECTED, sub-dollar tolerance)
  documented as design decisions.