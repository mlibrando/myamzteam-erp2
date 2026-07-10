# Claude Code Task — AU verification against Sellerboard (different target, same Amazon source)

> **SUPERSEDED — this brief's central inference is backwards.** Body left as written; it is the
> reasoning history. Corrected by [`AU_SELLERBOARD_VERIFICATION.md`](AU_SELLERBOARD_VERIFICATION.md)
> and by the code (`backend/sync/sellerboard.py`).
>
> - **Steps 2 / 3 and the Definition of Done are wrong: Sellerboard's `netProfit` uses
>   `productCosts`, NOT `salesCosts`.** Proven to the cent across all six months by
>   `sellerboard.assert_net_reproduces`, which also asserts the identity
>   `salesCosts = productCosts − costOfMissingReturns − missingFromInboundCosts`.
>   `salesCosts` remains the right basis for the **cog cell** — it is what our refund-netted,
>   `listTransactions`-derived cog can see — but not for **net**. The instruction "Commit
>   `salesCosts` as the cog basis for AU net" must not be followed.
> - **The inventory-loss gap is −$705.39, not ~$845** (the $845 was an addition error).
> - **This brief's parser rule was falsified by the 2026-07-09 re-pull.** Do **not** filter on
>   `has_data` or `status:"preparing"` — both moved between pulls. The summary row is identified by
>   `is_totals`, the in-progress month structurally, by not ending on its month's last day.
>   `sellerboard.py`'s docstring says exactly this; its loader still filters on both. See
>   [`../data/decisions_audit.md`](../data/decisions_audit.md) D1.2.

## Context

AU reconciles against **Sellerboard**, not Sellerise. The SP-API data is the same Amazon source as
every other marketplace — only the *target* differs. So this is a translation + verification layer,
NOT a new engine. `SELLERBOARD_RAW_DATA.json` is in `reference/data/`.

Sellerboard's structure differs from Sellerise in ways that will silently corrupt AU if assumed
away. The following were established by analyzing the file — **verify each against the real data,
do not take them on faith:**

1. **Sign convention is flipped.** `amazonFeesTotal`, `productCosts`, `advertising`,
   `refundCostsTotal`, `shippingCost` are already **negative** and net is built by *adding* them —
   opposite of Sellerise's subtract-a-positive-object model. A pipeline assuming Sellerise signs
   will get every cost line wrong-signed.
2. **Net uses `salesCosts`, not `productCosts`.** Reconstructing `netProfit` from gross
   `productCosts` comes up short by exactly `costOfMissingReturns` every month.
   `salesCosts = productCosts − costOfMissingReturns` (COGS after adding back returned-sellable
   items) held in 5/6 months; Jan/Jun also involve `missingFromInboundCosts`. This is the
   Sellerboard analog of the US "expenses-excluded-from-net" gotcha.
3. **`grossProfit == netProfit` in all 6 months** — this AU account has no manual expenses/VAT/
   external ads in Sellerboard, so the two collapse. Confirm this holds; if a future month diverges,
   the formula must handle both.
4. **Parser must skip two junk rows:** the leading `is_totals:true / has_data:false` summary and the
   trailing `status:"preparing" / has_data:false` partial-period stub. Ingesting either as a month
   corrupts everything.
5. **Periods are calendar months** (Unix ts decode to 2026-01-01 … 2026-06-30). Verify each period's
   boundaries rather than assuming.

## Operating rules

- **Verify thoroughly, diagnose properly.** Every mapping/sign/formula claim above is confirmed
  against the real file before it's committed. State results as numbers.
- Minimalist: a Sellerboard→our-schema translation + the AU reconcile run. No engine changes.
- Same discipline as prior marketplaces: same-signed material residual = systematic (investigate);
  small mixed-sign = drift (accept). Do not accept a residual by elimination.

## Step 1 — Parse + field-map Sellerboard correctly

- Load `SELLERBOARD_RAW_DATA.json`; skip the totals row and the preparing stub; keep the 6
  has_data periods. Assert each period is a full calendar month.
- Build the Sellerboard→our-P&L field map with **explicit signs**. Map to our buckets:
  - `sales` → revenue (verify: is it net of promotions? gross? compare to our chargesObject build)
  - `amazonFeesTotal` and its `amazonFees[]` detail → feesObject + fbaObject + storageFee
    (Sellerboard bundles referral, FBA per-unit, storage, subscription, reversal reimbursement,
    warehouse damage into one array — split them to our buckets)
  - `advertising` (+ `advertisingDetails[]`: sponsoredAds/videoAds/sponsoredDisplay/hsa) → adExpenses
  - `refundCostsTotal` and its `refundCosts[]` detail → refundsObject
  - `productCosts` / `salesCosts` / `costOfMissingReturns` → cog (see Step 3)
  - `shippingCost`, `missingFromInboundCosts` → the appropriate bucket/expenses
- Flag any Sellerboard field with no home in our schema, and any of our buckets with no Sellerboard
  source (e.g. does Sellerboard expose a salesTaxes/GST equivalent? `vatTotal`/`vatFacilitator` are 0
  here — confirm GST handling).

## Step 2 — Lock the net formula (verify the salesCosts inference)

- Reconstruct Sellerboard `netProfit` from the mapped components using **`salesCosts`** (netted COGS)
  and the flipped signs. It must reproduce `netProfit` to the cent for all 6 months.
- Prove the `productCosts`-vs-`salesCosts` choice by showing the `productCosts` version is off by
  exactly `costOfMissingReturns` each month. Commit `salesCosts` as the cog basis for AU net; do not
  guess.

## Step 3 — The actual test: reconcile OUR AU SP-API data against Sellerboard

This is the point of the task — everything above is setup.

- Run our AU pipeline (`listTransactions`-derived, purchase-date attribution, the AU mappings staged
  during the rollout probe: GST `Shipment.Tax` → passthrough, `ShippingTaxDiscount`, `ServiceFee.Promo`)
  and produce our per-month AU P&L in the same bucket shape.
- Diff our buckets against the Sellerboard-mapped targets, per month, per bucket: revenue, fees
  (referral/FBA/storage), ads, refunds, cog (via salesCosts basis), net. Show ours / theirs / Δ / Δ%.
- **AU-specific unknowns to resolve here, since AU was never reconciled before:**
  - GST: verify AU GST is genuinely pass-through and our `Shipment.Tax → passthrough` mapping makes
    revenue/net reconcile (this was *inferred* from CA/UK, never verified — it's now testable).
  - Refund + refund-COGS basis: run the both-bases test (posted vs purchase) for AU as done per
    marketplace; do NOT inherit US/CA/UK's answer.
  - AU cog values: Sellerboard's `Value of returned items` in `refundCosts[]` is the returned-unit
    COGS directly — cross-check our returned-unit cog netting against it.

## Step 4 — Diagnose residuals with the standard discipline

- For each bucket residual: same-signed across months = systematic (find the mechanism — cog basis,
  a mis-signed line, a mis-mapped Sellerboard field); small mixed-sign = drift (accept).
- Because AU reconciles against a **different tool**, do not assume Sellerise-market residual patterns
  transfer. Restatement/snapshot behavior may differ; establish AU's own drift characteristics.
- Any residual ends **named by test**, not by elimination or by analogy to the other markets.

## Step 5 — Bands + guard for AU

- Derive AU drift bands from AU's own observed drift (AU is small-scale like CA — US/UK dollar bands
  would be far too loose). Wire AU into both guards; verify 0 INVESTIGATE on the clean reconciled
  state and that the cog×1.20 perturbation fires.

## Guardrails

- Verify the flipped signs, the salesCosts-not-productCosts net basis, and the junk-row skipping
  against the real file before committing — these are the three silent-corruption risks.
- Do not inherit AU's GST/refund-basis answers from CA/UK; test them against Sellerboard.
- Do not widen tolerance to force AU net; leave residuals visible and named.
- Do not touch US/CA/UK numbers.

## Definition of done

- Sellerboard parsed (junk rows skipped, calendar months asserted); field map with explicit signs
  committed, unmapped fields/buckets flagged.
- Net formula reproduces Sellerboard `netProfit` to the cent (salesCosts basis proven vs productCosts).
- Our AU SP-API P&L reconciled against Sellerboard per bucket/month; GST pass-through and refund /
  refund-COGS basis verified for AU (not inherited).
- Residuals named by the same-signed/mixed-sign test, with AU's own drift characteristics established.
- AU wired into both drift guards with AU-scaled bands; clean state 0 INVESTIGATE, perturbation fires.
- No US/CA/UK change; no tolerance widened.