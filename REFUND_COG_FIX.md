# Claude Code Task — Net refund units out of COGS (test basis first, then implement)

## Context

The net residual diagnosis (`reference/data/net_residual_diagnosis.md`) traced the flat
~−$1,340/month net gap to `cog`: `cogs.py` subtracts COGS for *shipped* units
(`Shipment.items.quantity_shipped × cog_per_sku`) but never adds it back for *returned* units.
So every refund leaves its cost of goods stuck in net — a systematic over-subtraction carrying
94% of the −$8,042 cumulative residual. Verdict is solid; this task fixes it.

**One thing must be tested before implementing, not assumed:** the date basis for refund COGS.
The recorded fix design says "purchase-date basis, all statuses," but the evidence points the
other way. On the revenue side you already proved Sellerise books refunds on **processed date**
(postedDate beat PurchaseDate 6×). A refund's COGS is part of that same refund event, so it
should follow the same date rule its dollars do. And the diagnosis itself shows Jan/Feb stay
large *because* purchase-date basis re-attributes Dec-2025-order refunds out of Jan — which is a
symptom of the wrong basis, not a clean boundary residual. So test both bases; don't inherit the
default.

## Operating rules

- **Test the basis before committing the fix.** Compute refund COGS both ways, diff against the
  residual, and let the numbers pick the basis — same discipline that chose processed-date for
  refund dollars.
- Minimalist: one new monthly quantity (`refund_cog_by_month`) subtracted from `cog` before it
  feeds `pnl_monthly` and `_compute_net_ours`. No new dependencies, no reshaping of the pipeline.
- Change one variable at a time; measure net before/after; don't widen tolerance.

## Step 1 — Build `refund_cog_by_month` (both bases)

- Mirror the existing shipment COGS join, but source units from **Refund** transactions'
  `items.quantity_shipped` (units returned) × `cog_per_sku`, all statuses.
- Compute it **two ways**, keyed by month:
  - **processed-date** basis (month of the refund's `postedDate`) — the hypothesis, matching how
    refund *dollars* are already bucketed;
  - **purchase-date** basis (month of the original order's PurchaseDate) — the recorded design.
- Do not write anything into net yet.

## Step 2 — Test which basis closes the residual

- For each month Jan–Jun, subtract each candidate `refund_cog_by_month` from `cog` and re-diff
  net vs Sellerise. Produce a side-by-side table: net Δ today, net Δ with processed-date refund
  COGS, net Δ with purchase-date refund COGS.
- Read the result against the known tell: **if processed-date is correct, Jan/Feb should improve,
  not stay large.** The diagnosis showed purchase-date leaves Jan/Feb at −$2,018 / −$914 because
  Dec-order refunds re-attribute out of Jan. If processed-date keeps those refunds' COGS in the
  month they were processed and Jan/Feb collapse toward zero, that confirms the basis.
- Pick the basis that minimizes the residual across settled months (not just one month). Record
  the winner and the per-month numbers.

## Step 3 — Implement the winning basis

- Subtract the chosen `refund_cog_by_month` from monthly `cog` in `sync/cogs.py` **before**
  writing `pnl_monthly` and before `_compute_net_ours`.
- Re-run the full report. Emit net before/after per month and cumulative. Confirm the residual
  collapses toward zero across settled months.
- Whatever remains after the correct basis is the **genuine** accepted residual — quantify it per
  month and cumulatively, and label it precisely (the pre-2026-01-01 backfill boundary + any real
  Sellerise refund-policy sub-difference). Do **not** label self-inflicted basis error as
  "accepted residual" — that's the distinction this task exists to make.

## Guardrails

- If Step 2 shows *neither* basis meaningfully closes the residual, **stop and report** — the
  mechanism may be more than refund-unit netting (e.g. a cog_per_sku unit-basis mismatch, or
  Sellerise nets refund COGS at a different rate). Don't force a fix that doesn't close it.
- Refund COGS uses the same `cog_per_sku` as shipments; if a returned SKU has no cog rate, log it
  (mirrors the shipment-side fallback) rather than silently zeroing.
- Leave revenue lines, the ads reconciliation (PASS_DRIFT), and decisions A–G untouched. This
  touches `cog` only.
- Don't widen tolerance to make −3.84% "pass" — the goal is to close it, then accept only what's
  genuinely irreducible.

## Definition of done

- `refund_cog_by_month` computed both bases; Step 2 side-by-side table produced; winning basis
  chosen by residual reduction across settled months, with Jan/Feb behavior explicitly checked.
- Winning basis subtracted from `cog` before `pnl_monthly` / `_compute_net_ours`; report re-run
  with net before/after; residual collapsed toward zero for settled months.
- Remaining residual quantified and labeled with its real cause (backfill boundary / refund-policy
  sub-difference) — not mislabeled, not absorbed into tolerance.
- Missing-rate returned SKUs logged, not silently zeroed.
- If neither basis closes it: no fix applied, findings reported instead.