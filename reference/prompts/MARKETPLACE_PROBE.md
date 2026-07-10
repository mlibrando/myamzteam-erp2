# Claude Code Task — CA/UK/AU rollout probe (Sellerise side verified; now verify the SP-API side)

## Context

US reconciliation is complete and monitored. Extending to CA, UK, AU. The CA and UK Sellerise
responses have already been analyzed and the US P&L math **reproduces CA and UK net to the cent
across all 12 months** — same `revenue = Σ chargesObject`, `salesTaxes = Σ tax leaves`, and
`net = revenue − salesTaxes − fees − fba − refunds − storageFee − cog − ads`. So the engine
transfers; this is an extension, not a rebuild.

Three Sellerise-side facts are now established (do NOT re-derive — verify only on the SP-API side):

1. **Tax is still pass-through.** UK VAT and CA tax behave like US facilitator tax in Sellerise:
   `salesTaxes` equals the tax leaves in `chargesObject`, and refunds carry the net-zero
   `Tax` / `Tax Withheld` pair. The US tax mapping treatment holds — no mapping change expected.
2. **New fee class: `DigitalServicesFee` (and UK `DigitalServicesFeeFBA`).** Appears in
   `feesObject` (negative — reduces net; UK Jan −52.02) and in `refundsObject` (small positive —
   its reversal; CA + UK). This is the one net-affecting item **not in the US `bucket_map`
   vocabulary.**
3. **A few minor UK-only leaves:** `other-transaction` in `expenses`, and UK May/Jun
   `storageFee = 0` while FBA/storage-ish items sit in `expenses`.

The **SP-API-side leaf names** behind all of these are unknown — Sellerise's label is not
necessarily Amazon's `breakdownType`. That's the gap this probe closes.

## Operating rules

- **Verify, don't build, don't assume.** No rollout pipeline code. Probe real CA/UK/AU
  transactions and report observed values. Every matrix cell is evidenced or marked UNKNOWN.
- Reuse existing library clients (`Marketplaces.CA/.UK/.AU`) and the US probe/reconcile logic
  read-only.
- Where a Sellerise-side fact is already verified (above), confirm it once on the SP-API side and
  move on — spend the effort on the genuine unknowns.

## Probe 1 — `DigitalServicesFee` SP-API leaf (highest priority)

This is the one confirmed net-affecting difference. Find how it arrives from the API.

- Pull a settled month of `listTransactions` for UK and CA and locate the leaf `breakdownType`(s)
  that produce Sellerise's `feesObject.DigitalServicesFee` and `DigitalServicesFeeFBA`. Record the
  exact Amazon leaf string(s) — they may differ from Sellerise's label.
- Determine which transaction type / nesting carries it (its own leaf under Shipment? a separate
  service-fee transaction?) and its refund counterpart (the `refundsObject.DigitalServicesFee`
  positive reversal).
- Decision to surface (don't apply): map DSF/DSF-FBA into `feesObject` (net-affecting) with the
  status split like other fees, and its reversal into `refundsObject`. Confirm the leaf name so the
  mapping is grounded, not guessed.

## Probe 2 — Tax model confirmation (verify-once, expected SAME-AS-US)

- For one UK and one CA settled month, inventory the tax `breakdownType` leaves from
  `listTransactions` and confirm they map to the same pass-through treatment as US (collected in
  charges, net-zero remittance, `salesTaxes` = sum of tax leaves). Note the UK/CA-specific leaf
  names (VAT vs MarketplaceFacilitatorTax) even though the *treatment* is the same.
- Only escalate if the SP-API side contradicts the Sellerise-side pass-through result. Expected:
  confirmed same-as-US with different leaf names.

## Probe 3 — Refund + refund-COGS basis per marketplace (don't inherit US's answer)

- Run the same both-bases test used on US, per marketplace: refund *dollars* (posted vs purchase
  date) and refund *COGS* (posted vs purchase date) vs that marketplace's Sellerise `refundsObject`
  / `cog`. US chose purchase-date for refund COGS empirically — do not assume CA/UK/AU match.
- Record the winning basis per marketplace. Differing → per-marketplace basis config.

## Probe 4 — Unmapped-leaf census + minor UK items

- Run the US `bucket_map` against one settled month of each marketplace's transactions; report the
  **unmapped-leaf count and the exact leaf names**. US hit 0; anything here names precisely what
  needs a decision (expect at least the DSF leaves and UK `other-transaction`).
- Resolve the UK `storageFee = 0` months: confirm which SP-API leaf feeds UK's storage line and why
  May/Jun show 0 (genuinely no storage fee, vs a leaf we'd route to `expenses`). Identify the
  `other-transaction` leaf's SP-API source and whether it's net-affecting or belongs in `expenses`.

## Probe 5 — Currency, accounts, ads per marketplace

- Confirm native currency (CAD/GBP/AUD) flows through with **no FX** and amounts are in currency
  units (not micros), same as US.
- Confirm account/profile resolution per marketplace (`adsAccounts/list` → `advertiserAccountId`),
  that the Ads pull works per marketplace with `Amazon-Ads-ClientId`, and the `adProduct.value` set
  (US had SP/SB/SD only — confirm whether UK/CA/AU expose SB Video or SB TV; note CA/UK Sellerise
  show `hsaVideoCost` populated, so verify how that maps given no SB-Video adProduct value in US).
- **AU has no Sellerise file yet** — flag that AU cannot be reconciled until its target is provided;
  probe its transaction structure anyway so the differences are known.

## Deliverable — a differences matrix, evidenced

`reference/data/marketplace_rollout_probe.md`: per-marketplace × per-dimension (tax leaves + model,
DigitalServicesFee leaf + handling, refund basis, refund-COGS basis, currency/denomination, ads
account + adProduct set + SB-Video handling, unmapped leaves, storage/other-transaction, scale).
Each cell: **SAME-AS-US**, a specific difference, or **UNKNOWN**. For each difference, classify
**config change** vs **mapping/logic change** (the DSF fee is the leading mapping change).

## Guardrails

- Do not build the rollout or change any US code / accepted number.
- Sellerise-side facts above are verified — confirm on the SP-API side, don't re-litigate.
- No cell assumed from US without a CA/UK/AU number behind it; AU largely UNKNOWN pending its
  Sellerise target.

## Definition of done

- `DigitalServicesFee` / `DigitalServicesFeeFBA` SP-API leaf name(s) identified, with the
  fees-bucket + refund-reversal mapping decision surfaced (not applied).
- Tax model confirmed same-as-US on the SP-API side per marketplace, with the VAT/GST leaf names
  recorded.
- Refund and refund-COGS winning basis recorded per marketplace.
- Unmapped-leaf census per marketplace; UK `other-transaction` and `storageFee=0` resolved.
- Currency/ads/account structure confirmed per marketplace; SB-Video mapping question answered;
  AU gaps flagged (no Sellerise target yet).
- Differences matrix complete, each cell evidenced, differences tagged config vs mapping. No
  rollout code written.