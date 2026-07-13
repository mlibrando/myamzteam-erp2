# Claude Code Task — CA + UK rollout: verify the open mappings, then build (AU quarantined)

## Context

The rollout probe (`reference/data/marketplace_rollout_probe.md`) confirmed the US engine
reproduces CA/UK net to the cent, tax is pass-through with per-marketplace leaf names, and the
ads/currency/account plumbing is config-only. It proposed a set of `bucket_map` additions. Most
are solid. This task builds the **CA + UK** rollout — but **three of the proposed mappings/steps
are not yet verified and must be tested before they're committed.** AU stays out (no Sellerise
target).

Do not treat the probe's proposed mappings as final. Two of this project's hardest bugs came from
plausible-but-untested labels (US "V2 boundary", US "attribution drift"). The checks below are
cheap and run against data already pulled.

## Operating rules

- **Verify the open items BEFORE committing their mapping.** Each has a numeric target already
  available — hit it, don't assume it.
- Minimalist: add per-marketplace config + the verified `bucket_map` rules. No engine changes; the
  formula is unchanged. Reuse US reconcile/guard code per marketplace.
- Change one marketplace at a time; reconcile CA and UK each to the cent (settled months) before
  calling either done.

## Gate 1 — Verify `ShippingTaxDiscount` routing (likely mis-proposed — TEST FIRST)

The probe proposes `Shipment.ShippingTaxDiscount → chargesObject.ShippingTax`. **This is not
verified and may break a bucket that currently reconciles.**

- Using the UK Mar transaction JSON already pulled, sum the ShippingTax-family leaves two ways:
  (a) **including** `ShippingTaxDiscount` (−$18.74), (b) **excluding** it. Sellerise UK Mar
  `chargesObject.ShippingTax` = **$25.89** (exact target).
- If (a) hits 25.89 → the fold-in is correct, commit it. If (b) hits 25.89 and (a) overshoots →
  `ShippingTaxDiscount` does NOT belong in ShippingTax; find its real home (candidate: a discount
  line or `expenses`) by which routing makes the month reconcile. Do the same for
  `Refund.ShippingTaxDiscount` against `refundsObject.ShippingTax`.
- Commit only the routing that hits the Sellerise target. Report both sums and the decision.

## Gate 2 — Per-marketplace refund + refund-COGS basis (do NOT inherit US)

- For CA and UK, run the same both-bases test used on US: refund *dollars* (posted vs purchase
  date) and refund *COGS* (posted vs purchase date) vs that marketplace's Sellerise
  `refundsObject` / `cog`. Requires the per-marketplace Orders API sweep (with the Dec buffer)
  first — do that sweep as part of this gate.
- Record the winning basis per marketplace. US chose posted-date (dollars) / purchase-date (COGS)
  — CA/UK may differ. Wire the winning basis per marketplace; do not hardcode US's answer.

## Gate 3 — Close the UK May/Jun unknowns (small pulls)

- Pull UK May and Jun `listTransactions` (not in the Mar probe sample). Identify the SP-API leaf
  behind Sellerise UK `expenses.other-transaction` (May −$113.68 / Jun −$132.85) and resolve why
  UK `storageFee = 0` those months (genuinely no `ServiceFee.FBAStorageFee`, vs a renamed leaf).
- Classify `other-transaction`: net-affecting or `expenses` (excluded)? Confirm against whether
  including/excluding it makes UK May/Jun net reconcile. Commit accordingly.

## Build (after Gates 1–3 pass)

Apply the verified mappings to `bucket_map.py` (each with the status split where applicable):

- `("Shipment","DigitalServicesFee",*)` → `feesObject.DigitalServicesFee`  (UK; leaf name verified)
- `("Shipment","DigitalServicesFeeFBA",*)` → `feesObject.DigitalServicesFeeFBA`  (UK)
- `("Refund","DigitalServicesFee",*)` → `refundsObject.DigitalServicesFee`  (CA + UK; positive reversal)
- `ShippingTaxDiscount` (Shipment/Refund) → **the routing Gate 1 verified** (not assumed)
- Add `MarketplaceFacilitatorVAT-Principal/-Shipping` to the passthrough tax family (UK) and to
  `_REFUND_TAX_WITHHELD_TYPES` (UK refund `Tax Withheld`)
- CA tiny `Shipment.Tax` (−$1.32) → per Gate 1/tax family (verify it's the CA facilitator leaf,
  not something else, given how small it is)

Config (no logic delta): per-marketplace COGS sheet (already keyed), ads `budget_currency` filter
(CAD/GBP), per-marketplace Sellerise target path, per-marketplace Orders sweep + attribution.

Then reconcile CA and UK each: run the full report per marketplace, all six months, and confirm
settled months reconcile to the cent (within the same tolerance/drift bands as US, adjusted for
each marketplace's scale). Run the drift guards per marketplace.

## AU — QUARANTINED, do not build

- AU has **no Sellerise target** (`SELLERISE_RAW_DATA_AU.json` missing), so AU cannot be
  reconciled or its mappings verified. Do NOT commit AU mappings (`Shipment.Tax` GST →
  passthrough, `ServiceFee.Promo`, AU `ShippingTaxDiscount`) as final — they are inferences from
  CA/UK, not AU measurements.
- Record the AU structural findings as PENDING. The AU GST-passthrough assumption in particular is
  unverified and must be tested against the AU Sellerise target when provided — flag it explicitly
  as an assumption, not a confirmed mapping.

## Guardrails

- No proposed mapping is committed without hitting its Sellerise target number (Gates 1–3).
- Do not inherit US's refund basis for CA/UK — test per marketplace.
- Do not build AU. Do not change US code, mappings, or accepted numbers.
- Per-marketplace drift bands derive from each marketplace's observed drift, not copied from US
  (CA/UK are ~1/10th US scale — US dollar bands would be far too loose).

## Definition of done

- Gate 1: `ShippingTaxDiscount` routing decided by hitting UK Mar ShippingTax = $25.89; both sums
  reported.
- Gate 2: CA and UK refund + refund-COGS winning basis recorded and wired per marketplace.
- Gate 3: UK `other-transaction` SP-API leaf identified and classified; `storageFee=0` explained.
- CA and UK each reconcile settled months to the cent with per-marketplace drift bands; guards run
  clean.
- Verified `bucket_map` rules committed; AU mappings left PENDING with the GST-passthrough
  assumption explicitly flagged as unverified.
- Write-up updated; no US number changed.