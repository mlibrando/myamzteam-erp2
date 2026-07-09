# Claude Code Task — AU currency resolved: verify the three-currency picture, then build the adapter

## Context

The AU currency confusion is resolved. Three facts, each established from a different source — **but
each must be re-verified against the data before anything is built.** The whole AU build hinges on
them, and a wrong assumption here produces a clean ~33–50% error that still *looks* like a number.

| side | currency | evidence |
|---|---|---|
| SP-API AU transactions (our pipeline) | **AUD** | native-currency architecture |
| Sellerboard AU (reconciliation target) | **USD** | confirmed in Sellerboard account settings |
| AU COGS workbook sheet | **USD** (despite being labeled AUD) | retail column shows 133.97 (US price 130.95; in AUD it'd be ~195); cost 30.99 ≈ Sellerise-US 30.76 USD; margin 77% == US margin 77% |

Supporting arithmetic (verify, don't inherit):
- FX per the margin-analysis sheet: **AUD→USD = 0.67**, GBP→USD = 1.36.
- This explains every observed ratio: revenue/referral/FBA all ≈ **0.68** (Sellerboard USD vs our AUD
  = real FX), while cog ≈ **1.05** (Sellerboard USD vs sheet USD = same currency, small real drift
  like UK's).

**Consequence — the trap this task exists to avoid:** the pipeline assumes each marketplace's
workbook is in that marketplace's native currency. **For AU that is false.** If the FX adapter
converts the AU workbook, cog lands ~33–50% wrong. AU cog is **USD, do-not-convert**; AU
transactions are AUD.

## Operating rules

- **Verify before building.** Every currency claim above gets an arithmetic check first. Do not
  build on a stated fact — build on a measured one.
- Minimalist: FX belongs in the **AU-target adapter only**. Preserve the pipeline's native-currency
  invariant. No engine rewrite.
- Same residual discipline as always: same-signed material = systematic; small mixed-sign = drift.
  Never relabel FX-math noise as a reconciliation result, and never let a real gap hide behind "FX."

## Step 1 — Verify the three-currency picture arithmetically (gate; do not skip)

Independent of anyone's say-so, confirm each side's currency from data:

1. **Sellerboard is USD / pipeline is AUD.** Compute `sellerboard.sales ÷ our_AUD_chargesObject.Principal`
   per month. Expect ≈ **0.67–0.68**, stable. Do the same for referral/commission and FBA per-unit
   fee. If all three agree tightly → confirmed FX, and the *measured* rate is your reference rate.
2. **Currency-proof cross-check:** compare **units and orders** (counts, not money) between
   Sellerboard and our AU pipeline per month. If counts match but dollars differ by ~0.67, it's the
   same transactions in a different currency (FX). **If counts also differ, it is NOT currency** —
   it's a scope/date-basis problem. Stop and report; do not build the adapter.
3. **AU workbook is USD.** Assert the AU sheet's cost values are USD-magnitude: GMAKER-3 ≈ 30.99
   (≈ US 30.76), not ≈ 46. Cross-check a second SKU where USD/AUD magnitudes diverge visibly
   (MBUKB1 or an MB2E bundle). Confirm `sellerboard.productCosts ÷ our_cog(from USD sheet)` ≈ 1.0,
   **not** 0.67 — that's the proof both sides are USD.

If any of the three fails, **stop and report.** Do not proceed to build on a falsified premise.

## Step 2 — Pin the FX rate to what Sellerboard actually used

- Do not apply an "externally correct" rate Sellerboard never used. Back out the **implied monthly
  rate** per bucket (Step 1.1). If revenue-implied and fee-implied rates agree within a month,
  Sellerboard effectively used one monthly rate → a month-level conversion is safe. If they diverge,
  Sellerboard converted at finer granularity → a monthly rate leaves a residual you must account for.
- Compare the implied rate to the sheet's 0.67. Report both. Use the implied rate for reconciliation
  (goal: reproduce Sellerboard's conversion, not an idealized one).

## Step 3 — Build the adapter (narrow)

- Convert **Sellerboard USD → AUD** at the Step-2 rate; keep the pipeline native AUD. FX lives only
  in the AU-target adapter.
- **AU cog: mark USD, DO NOT CONVERT.** Add an explicit per-marketplace workbook-currency flag
  (e.g. `MARKETPLACE_COG_CURRENCY = {AU: "USD", ...}`) so the sheet's currency is never inferred from
  the marketplace again. Assert in code that AU cog is not double-converted.
  - Decide and document how AU cog joins an AUD pipeline: either convert the USD cog → AUD once for
    the pipeline, or compare AU cog in USD against Sellerboard's USD directly. **Pick one explicitly;**
    ambiguity here is exactly what caused this whole detour.
- Guard: assert GMAKER-3's effective AU cog lands at its expected value under the chosen scheme
  (≈30.99 USD, or ≈46 AUD) — never ≈21 or ≈69 (the two double-conversion failure modes).

## Step 4 — Reconcile, reporting FX and reconciliation residuals SEPARATELY

- Per bucket, per month: emit **(a)** the FX-conversion residual (expected, from rate averaging) and
  **(b)** the post-FX reconciliation residual (our pipeline vs Sellerboard). **Never merge them** —
  merging is how a real error hides behind "it's just FX."
- Post-FX, revenue/fees/FBA should reconcile near-zero. If a residual is same-signed and material,
  the rate or granularity is wrong, or there's a real gap — diagnose, don't accept.
- cog should reconcile at ≈1.0 with only small drift (UK-like, workbook-vs-target cost differences).

## Step 5 — Named, non-drift differences (carry forward, don't rediscover)

- **~$845 inventory-loss gap:** Sellerboard's `productCosts` deducts `costOfMissingReturns +
  missingFromInboundCosts`, which we cannot see from `listTransactions`. Match bases explicitly
  (compare our cog to `salesCosts`, or add the gap when targeting `productCosts`/net). Label a
  **known source-of-data difference, NOT drift.**
- **Net basis:** Sellerboard's `netProfit` uses **`productCosts`** (verified — an earlier brief had
  this backwards). Reproduce `netProfit` to the cent before trusting any net comparison.
- **Parser:** skip the `is_totals` row and the `status:"preparing"` stub; `refundCostsTotal` is
  **signed, not always negative** (Jun = +30.99).
- **GST:** Sellerboard has no GST/VAT line (all zeros), so `Shipment.Tax → passthrough` **cannot be
  verified against this target.** Record AU GST as **inferred, not verified.** A clean net does not
  prove GST — do not claim it does.
- **`order_purchase_date` has 0 rows for AU** → the refund/refund-COGS both-bases test cannot run.
  Backfill AU orders via `getOrders` first, or state explicitly that AU refunds default to
  posted-date and the basis is untested.

## Step 6 — CA guard (a latent trap this investigation exposed)

CA is marked done, and its fix redirected CA cog to **US (USD)** values. Sellerise CA displays
**41.53 CAD** (= 30.76 × ~1.35, properly converted). So verify: **is the CA workbook sheet CAD or
USD?** Apply the same test used for AU — read CA's retail column. If it's USD-magnitude (~130, not
~180), then CA reconciled *because* both sides were effectively USD, and that dependency must be
documented in `MARKETPLACE_COG_CURRENCY`, not left implicit. Report the finding; change no CA number.

## Guardrails

- Any of Step 1's three checks failing ⇒ stop and report. Never build on a falsified premise.
- Never double-convert AU cog. Assert the guard value.
- Report FX residual and reconciliation residual as separate numbers, always.
- Use Sellerboard's *implied* rate, not an idealized external rate.
- Do not touch US/UK; do not widen tolerance; do not change CA numbers (Step 6 is read-only).

## Definition of done

- Step 1's three currency claims verified arithmetically (incl. the currency-proof units/orders check).
  Any failure reported, not worked around.
- Implied monthly FX rate reported per bucket and compared to the sheet's 0.67; granularity chosen by data.
- Adapter converts Sellerboard USD→AUD only; `MARKETPLACE_COG_CURRENCY` added with AU=USD; the
  no-double-conversion assert passes on GMAKER-3.
- Per-bucket reconciliation with FX residual and post-FX residual reported **separately**; revenue/
  fees/FBA near-zero post-FX; cog ≈1.0 with drift only.
- Named non-drift differences documented (inventory-loss gap, productCosts net basis, parser quirks,
  GST inferred-not-verified, AU refund basis untested pending `order_purchase_date` backfill).
- CA workbook currency verified and recorded; no CA/US/UK number changed.