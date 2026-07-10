# Claude Code Task — Re-verify AU against the updated Sellerboard file

## Context

`SELLERBOARD_RAW_DATA.json` has been re-pulled. The prior AU reconciliation cleared its currency
gate and reconciled 4/6 months, leaving **Jan** (shipment family implies 0.591 vs refunds' 0.674 —
proven a *content* difference, not FX) and **Mar** (shipment family 3.9% below reference)
unresolved. The new file is a natural experiment on the Jan hypothesis.

**Standing corrections — carry forward, do not re-litigate** (each was established against data):
- `netProfit` uses **`productCosts`**, not `salesCosts`.
- Inventory-loss gap = **−$705.39** (not $845).
- Sellerboard reports Amazon fees **GST-inclusive**; normalise AU's 10% GST on `Shipment.Tax` and
  `ServiceFee.Tax` leaves. Referral fee carries **no** GST.
- Reference FX rate derived **only from refunds + ads** (identical events / outside SP-API). Never
  fit the rate to revenue or fees — the buckets under test.
- FX band is an **absolute rate tolerance**, never a spread fitted to observed disagreement.
- Sellerboard converts **per transaction date**, not per month.
- Parser: skip `is_totals` row and `status:"preparing"` stub; `refundCostsTotal` is signed.
- AU workbook cog is **USD** (`MARKETPLACE_COG_CURRENCY`); never double-convert.

If the new file contradicts any of these, **that contradiction is the finding** — report it, don't
silently adopt it.

## Step 1 — Diff old vs new Sellerboard (the most informative step)

Compare the previous file against the new one, per month, per field (`sales`, `amazonFeesTotal`,
`productCosts`, `refundCostsTotal`, `advertising`, `netProfit`, units, orders, refunds).

Read the result:
- **Jan grew** (sales / fees larger) → consistent with Sellerboard having since ingested content it
  was missing. Do **not** declare the boundary hypothesis proven on growth alone (see Step 3).
- **Jan byte-identical** → Sellerboard's Jan is frozen; the content gap is structural, not a
  snapshot-timing artifact. The Dec-backlog story is dead.
- **Other months moved** → you have just measured **Sellerboard's restatement behaviour**. Record the
  magnitude per bucket; this is the empirical input AU drift bands will need later.

## Step 2 — Re-run the currency gate + reconcile

- Re-confirm: units/orders match per month (currency-proof); implied rate from refunds+ads is stable;
  GST normalisation still yields 9.99–10.01% on the two fee leaves.
- Re-run the reconcile. Report per-month, per-bucket: **FX residual** and **post-FX reconciliation
  residual**, separately (never merged).
- Specifically report whether **Jan's shipment-family implied rate has moved toward reference (~0.67)**
  and whether **Mar's 3.9% shifted**.

## Step 3 — If Jan changed, name the mechanism (don't infer it)

Growth is consistent with *both* a Dec-2025 backlog ingestion **and** ordinary restatement. Discriminate:

- Identify the specific transactions Sellerboard gained. Do they trace to **pre-2026-01-01 purchase
  dates / late-December postings** (backlog) or are they spread through January (restatement)?
- Only a transaction-level answer names it. "Jan grew, therefore backlog" is the plausible-label
  failure this project has caught three times.

## Guardrails

- **Do not wire AU drift bands.** Jan/Mar unresolved ⇒ any band fitted now is fitted to a contaminated
  baseline and would quietly certify the gap. Bands come after the residual is clean.
- Do not fit the FX rate to revenue/fees; do not widen tolerance to make a month pass.
- Same-signed material residual = systematic; small mixed-sign = drift. Never accept by elimination.
- Do not touch US/CA/UK numbers or reports.

## Definition of done

- Old-vs-new Sellerboard diff table (per month, per field), with Jan classified as grew / identical,
  and any other-month movement recorded as Sellerboard's restatement magnitude.
- Currency gate re-confirmed (units/orders, refunds+ads implied rate, GST normalisation).
- Reconcile re-run with FX and post-FX residuals reported separately; Jan's shipment-family rate and
  Mar's 3.9% explicitly re-stated.
- If Jan moved: mechanism named at transaction level (backlog vs restatement), not inferred from growth.
- Bands still unwired; Jan/Mar left named-or-open, never absorbed.