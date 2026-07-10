# Claude Code Task — AU purchase-date backfill, then name January and March

## Context

AU reconciles 4/6 months. Two months are open, and **one backfill unblocks both**:

- **Jan**: −$1,459 structural gap, proven permanent (Sellerboard's Jan is byte-identical across
  pulls; it restates only the trailing month, by cents — the Dec-backlog hypothesis is dead).
  Evidence points to purchase-date vs postedDate attribution: the excess is head-loaded (first two
  posting days carry 101% of the dollar excess), and the end-of-month story was ruled out on unit
  economics. **Filed as evidence, not verdict** — the dollar match sits in a ~4%-wide window and the
  head carries 11 units where 9 are needed.
- **Mar**: shipment family −3.85% below reference. Untested: Sellerboard converts **per transaction
  date**, so a per-transaction-date rate may explain it.

`order_purchase_date` has **0 AU rows**. That blocks (a) naming January and (b) AU's refund /
refund-COGS basis test — which must NOT inherit US/CA/UK's answer (CA already differs from US).

## Operating rules

- **Simplicity first.** This is a backfill + two tests. Reuse the existing `getOrders` sweep and the
  existing both-bases test. No new abstractions, no new dependencies, no engine changes.
- Verify, don't assume. Name residuals by test; never by elimination or plausibility.
- **Do not wire AU drift bands.** Jan/Mar open ⇒ any band fitted now certifies a contaminated baseline.

## Step 1 — Backfill `order_purchase_date` for AU

- Run the existing Orders sweep for `Marketplaces.AU`, `CreatedAfter=2025-12-01` (the Dec buffer is
  essential — January's hypothesis depends on December purchase dates existing).
- Same pattern as the US sweep: bulk `getOrders` date-range paging, persist `{AmazonOrderId:
  PurchaseDate}`, resumable, idempotent. Log fallback count/$ (orders with no purchase date).
- Nothing else changes. Don't touch attribution yet.

## Step 2 — Name January (the test the evidence has been waiting for)

- Identify the January excess transactions (the head-loaded 2–3 Jan postings) and check their
  **PurchaseDate**. Do they fall in **December 2025**?
- If yes: Sellerboard books by purchase date (so those land in its Dec, outside its window) while we
  book by postedDate (so they land in our Jan). That names the mechanism. Quantify: does re-keying
  January's shipments on PurchaseDate close the −$1,459 (or move it within January's own rate
  uncertainty band, 2,163–2,257 AUD)?
- If no: the head-loaded pattern has another cause. Report it; do not force the attribution story.
- Either way, state the verdict from the transaction-level dates, not from the head-loading pattern.

## Step 3 — March: per-transaction-date FX (independent, can run in parallel)

- Sellerboard converts per transaction date. Apply the **per-transaction-date rate** to March's
  shipment family instead of a monthly rate, and re-measure the −3.85%.
- Collapses to near-zero → date-mix within month; March is explained. Persists → March has a content
  difference like January's; report it, leave it named-or-open.

## Step 4 — AU refund + refund-COGS basis (now possible)

- With purchase dates present, run the existing both-bases test for AU: refund **dollars** (posted vs
  purchase) and refund **COGS** (posted vs purchase) against Sellerboard's refund lines / cog.
- Record the winner per basis. **Do not inherit** US (posted/purchase) or CA (posted/posted). Wire
  AU's answer into the existing per-marketplace config.

## Guardrails

- Reuse the existing sweep and both-bases test; write no new machinery.
- January is named only by December purchase dates on the actual excess transactions — "head-loaded,
  therefore purchase-date" is the plausible-label failure caught three times in this project.
- Bands stay unwired until Jan and Mar are both named.
- Standing corrections hold: `netProfit` uses `productCosts`; inventory-loss gap −$705.39; fees are
  GST-inclusive (10% on `Shipment.Tax` / `ServiceFee.Tax`, none on referral); reference rate from
  **refunds + ads only**; FX band absolute, never fitted; parser keys on `is_totals` + calendar-month
  completeness (the `has_data`/`status` flags are not durable).
- Do not touch US/CA/UK numbers or reports.

## Definition of done

- AU `order_purchase_date` backfilled from 2025-12-01, resumable/idempotent, fallbacks logged.
- January named at transaction level (December purchase dates confirmed or refuted), with the −$1,459
  quantified under purchase-date re-keying — or reported as not-that-mechanism.
- March re-tested with per-transaction-date FX; explained or left explicitly open.
- AU refund and refund-COGS bases chosen empirically and wired per-marketplace.
- Bands still unwired; no US/CA/UK change; no new abstractions.