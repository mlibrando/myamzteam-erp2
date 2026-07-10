# Claude Code Task — Close January (storage fee + S03), and check S03 across US/CA/UK

## Context

AU is named: Sellerboard books shipments on order **PurchaseDate** (counts match 5/6 months vs 0/6
for posted-date), which closed March for free. Refund bases measured, not inherited: dollars =
posted, COGS = posted (AU lands with CA). No AU per-unit cost gap — workbook equals Sellerboard.

**Five of six months reconcile. January is diagnosed but not closed.** Two named items remain:

1. **S03 finances-coverage gap.** Twelve `S03-`prefixed orders are `Shipped` in the Orders API but
   have **zero transactions** in `listTransactions`. The `249`/`250`/`503` prefixes all have them.
   January's cog gap is exactly **−$86.71** = MBUKB1's workbook cog, the only 1–2 unit combination
   summing to it; commission (−30.07) and FBA (−30.27) flags are the same orders' fees.
2. **Storage fee (−52.75).** Hypothesis: `FBAStorageFee` is arrears-billed and Sellerboard books it
   to December. **Untested — currently a plausible label, not a verdict.**

Bands stay unwired until January is clean.

## Operating rules

- **Simplicity.** Two small tests plus one read-only sweep. Reuse existing queries. No new machinery,
  no new dependencies, no engine changes.
- Name by test, never by plausibility. An untested hypothesis stays labeled untested.

## Step 1 — Test the storage-fee arrears hypothesis

- Direct check: does Sellerboard's **December 2025** carry an `FBAStorageFee` that corresponds to our
  January −52.75? (Requires Sellerboard Dec data — if a 12-month pull is available, use it; if not,
  say so and leave the item open rather than inferring.)
- Alternative in-data check: compare the `postedDate` of the AU `ServiceFee.FBAStorageFee`
  transactions against the storage period they bill for. If the January-posted fee bills a December
  period, that is consistent with arrears billing — but state it as consistent-with, not proven,
  unless Sellerboard's December confirms.
- Verdict: **explained** (with evidence) or **open** (explicitly untested). Do not assert.

## Step 2 — Characterize S03

- What distinguishes the 12 `S03-` orders? Check `fulfillmentChannel`, `salesChannel`, `orderStatus`,
  `orderType`, marketplace routing, and dates. Are they FBA/MFN? A different sales channel?
- Do they post **later**? Re-check `listTransactions` for those specific order IDs across the full
  window (not just January) — a delayed post would mean coverage lag, not a permanent gap.
- Confirm the arithmetic: do the missing S03 orders' expected fees account for January's
  commission (−30.07) and FBA (−30.27) flags, and does the MBUKB1 unit account for the −$86.71?
- Verdict: permanent Finances-API coverage gap, or delayed posting. Quantify either way.

## Step 3 — Does the S03 class exist in US/CA/UK? (read-only, parallel)

A Finances-API gap that drops shipped orders would be a systematic issue, not an AU quirk — and could
be sitting inside accepted residuals elsewhere (e.g. US's +1.70%).

- For US, CA, UK: count orders that are `Shipped` in `order_purchase_date` / Orders data but have
  **zero rows** in `sp_transactions`. Report count, $ exposure (estimate via workbook cog + expected
  fees), and any shared order-ID prefix or attribute.
- **Read-only.** Change no US/CA/UK number, mapping, or report. If a class exists, report it as a
  finding for a separate task — do not fix it here.

## Step 4 — Close or leave open, explicitly

- If both Step 1 and Step 2 resolve: January is clean; report AU's per-bucket reconciliation across
  all six months and state that bands may now be derived.
- If either stays open: say so plainly. January stays diagnosed-but-open, bands stay unwired.
- Do not absorb an open item into a tolerance to reach "clean."

## Guardrails

- Bands remain unwired unless January is genuinely clean.
- "Arrears-billed, therefore December" is a label until Sellerboard's December (or the billing-period
  field) confirms it. Four prior plausible labels in this project turned out wrong.
- Standing corrections hold: `netProfit` uses `productCosts`; inventory-loss gap −$705.39; fees
  GST-inclusive (10% on `Shipment.Tax` / `ServiceFee.Tax`, none on referral); reference rate from
  refunds + ads only; FX band absolute, never fitted; parser keys on `is_totals` + calendar-month
  completeness.
- **Settle bases on counts, not dollars** — a definition mismatch (e.g. `salesCosts` not netting
  returns) can invert both a dollar test and the mixed-sign heuristic.
- No US/CA/UK change. No new abstractions.

## Definition of done

- Storage fee: explained with evidence, or explicitly left open as untested.
- S03: characterized (permanent gap vs delayed post), with the −$86.71 / −30.07 / −30.27 arithmetic
  confirmed.
- US/CA/UK checked read-only for an S03-equivalent class; count and $ exposure reported as a finding.
- January stated plainly as clean or diagnosed-but-open; bands wired only if clean.
- No US/CA/UK number, report, or row changed; no new machinery.