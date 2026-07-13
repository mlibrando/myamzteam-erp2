# CA/UK/AU rollout probe — differences matrix (SP-API side)

Sellerise-side facts (US math reproduces CA/UK net to the cent across 12
months, tax is pass-through, `DigitalServicesFee[FBA]` is the one net-affecting
new fee, minor UK-only leaves) are **assumed verified** per the task brief.
This probe evidences the **SP-API side** and produces a per-dimension diff of
what changes for the rollout.

Data source: one settled month (2026-03) of `listTransactions` pulled per
marketplace via `Marketplaces.CA/.UK/.AU`. Raw JSON saved under
[reference/data/rollout_probe/](rollout_probe/). No code deployed; no US
number changed.

## Differences matrix

Legend per cell: **SAME-AS-US** · specific difference · **UNKNOWN** (probe
gap). Change class: **CFG** = config/data change · **MAP** = mapping/logic
change · **DEFER** = requires more data (usually an Orders API sweep or a
Sellerise target).

| dimension | US (baseline) | CA | UK | AU | class |
|---|---|---|---|---|---|
| **Tax leaf: charge-side** | `OurPriceTax` + `MarketplaceFacilitatorTax-*` (pass-through) | **SAME-AS-US** — MFT-Tax family present (`MarketplaceFacilitatorTax-Principal/-Shipping`) | Different leaf names but same treatment — `MarketplaceFacilitatorVAT-Principal/-Shipping` + `OurPriceTax` | Different: `Shipment.Tax` (GST, seen −$105 Mar) + `LowValueGoodsTax-Principal` | **MAP** — add VAT/GST leaves as passthrough family entries in bucket_map for UK and AU |
| **Tax leaf: refund-side** | `OurPriceTax` → `refundsObject.Tax`; MFT → `Tax Withheld` | **SAME-AS-US** | Same treatment; refund leaves are MFT-VAT variants | UNKNOWN — AU refund leaves in Mar sample had no distinct tax leaves | **MAP** for UK VAT; AU DEFER |
| **`DigitalServicesFee` leaf (fees)** | not present in US bucket_map | not present in Mar SP-API data (Sellerise Mar CA has 0 too) | **`Shipment.DigitalServicesFee` = −$116 Mar (RELEASED + DEFERRED_RELEASED sum)** — the exact Amazon `breakdownType` (name matches Sellerise's label to the letter) | not present | **MAP** — add `("Shipment", "DigitalServicesFee")` → `feesObject.DigitalServicesFee` with status split |
| **`DigitalServicesFeeFBA` leaf (fees)** | not present | not present | **`Shipment.DigitalServicesFeeFBA` = −$0.12 Mar** — very small but present in UK. Same name | not present | **MAP** — add `("Shipment", "DigitalServicesFeeFBA")` → `feesObject.DigitalServicesFeeFBA` |
| **`DigitalServicesFee` reversal (refund side)** | not present | **`Refund.DigitalServicesFee` = +$0.54 Mar** (positive — reversal of the fee) | **`Refund.DigitalServicesFee` = +$11.25 Mar** (also positive) | not present | **MAP** — add `("Refund", "DigitalServicesFee")` → `refundsObject.DigitalServicesFee` (positive = fee refunded to seller) |
| **`ShippingTaxDiscount` leaf (unmapped in US too)** | seen 0 times US | not seen CA | **UK Shipment −$18.74, Refund +$1.71** — new leaf, likely a tax-side discount on shipping | **AU Shipment −$3.38** — same leaf | **MAP** — add `Shipment.ShippingTaxDiscount` and `Refund.ShippingTaxDiscount`. Semantically: reversal of ShippingTax. Route to `chargesObject.ShippingTax` (Shipment) / `refundsObject.ShippingTax` (Refund) as a component |
| **AU `Shipment.Tax` (GST)** | n/a | n/a | n/a | **new leaf**, −$105 Mar. Likely a distinct GST leaf that doesn't match US MFT family | **MAP** — add `("Shipment", "Tax")` and `("Refund", "Tax")` (if seen) → passthrough (GST is pass-through per Sellerise-side confirmation for other marketplaces). Needs AU Sellerise target to verify |
| **AU `ServiceFee.Promo`** | n/a | n/a | n/a | new leaf, +$5.25 Mar. Small | **MAP** — deferred until enough Mar+other months' data to see if it's material |
| **UK `other-transaction` in expenses** | n/a | n/a | Sellerise UK May/Jun: `expenses.other-transaction` = −$113.68 / −$132.85. Not seen in Mar SP-API data | n/a | **DEFER** — need to pull UK May or Jun listTransactions to find the SP-API leaf that produces this |
| **UK `storageFee = 0` May/Jun** | storageFee always non-zero US | n/a | Mar UK storageFee = $148.08 (matches `ServiceFee.FBAStorageFee` sum exactly, US rule holds). **May/Jun: Sellerise `storageFee = 0`** and `expenses` gains `FBAFees` + `other-transaction` — Amazon probably reclassified UK storage those months | n/a | **DEFER** — pull May/Jun UK listTransactions to see whether `ServiceFee.FBAStorageFee` is genuinely 0 or has been renamed |
| **Currency** | USD | **CAD** native, no FX, currency units (sample totalAmount 51.75 CAD) | **GBP** native, no FX, currency units (89.09 GBP) | **AUD** native, no FX, currency units (230.99 AUD) | **CFG** — per-marketplace COGS workbook already switches by sheet; no code change |
| **Denomination** | currency units (not micros) | **SAME-AS-US** | **SAME-AS-US** | **SAME-AS-US** | — |
| **Refund basis (dollars)** | postedDate wins (empirical) | UNKNOWN — no Sellerise-driven basis test yet (needs Orders API sweep + refundsObject compare) | UNKNOWN | UNKNOWN (also missing Sellerise target) | **DEFER** — do per-marketplace both-basis test at rollout, mirroring US |
| **Refund-COGS basis** | purchase-date wins (empirical, Σ\|Δ\| $5,249 vs $5,971) | UNKNOWN | UNKNOWN | UNKNOWN | **DEFER** — same |
| **Ads account** | `amzn1.ads-account.g.a86z4ip0byyr0754l34817zfs` under NA endpoint | **Same account** — the NA "Magical Butter" account services all 18 country codes including CA, GB (UK), AU | Same account | Same account | **CFG** — no new ads account or token needed. Pull one Ads report as today; filter `budgetCurrency` per marketplace |
| **Ads-API access — EU/FE tokens** | AMAZON_ADS_REFRESH_TOKEN_NA present | not needed (NA account serves CA) | not needed (NA account serves GB) | not needed (NA account serves AU) | — |
| **`adProduct.value` values** | `Sponsored Products`, `Sponsored Brands`, `Sponsored Display` (SP/SB/SD; NO SB Video, NO SB TV) | **SAME-AS-US** — verified across all 4 currencies in the same NA report: still only 3 values | **SAME-AS-US** | **SAME-AS-US** | — |
| **SB Video handling** | merge `hsaCost + hsaVideoCost` into API's `Sponsored Brands` line | **Applies:** CA Mar `Sponsored Brands` (CAD) = $2.58 = Sellerise `hsaVideoCost` $2.58 (Sellerise treats CA's SB entirely as video for this month) | **Applies:** UK Mar `Sponsored Brands` (GBP) = $127.66 = Sellerise `hsaCost $12.21 + hsaVideoCost $115.45` = $127.66 exact | UNKNOWN — no Sellerise target | **CFG** — reuse US rule uniformly; per-marketplace ads sub-line split (hsaCost vs hsaVideoCost) not sourceable from API, matches Sellerise's own decomposition summed |
| **Ads `metric.totalCost` denomination** | currency units | **SAME-AS-US** (CAD/GBP/AUD amounts consistent with Sellerise adCost values) | **SAME-AS-US** | **SAME-AS-US** | — |
| **Ads sub-line targets Mar match** | US matched adCost / hsaCost+hsaVideo / sdCost / stvCost within ±$5.75 | **CA Mar exact: SP $1153.55, SB $2.58, SD $0** | **UK Mar exact: SP $1639.07, SB $127.66, SD $0** | UNKNOWN | — |
| **Sellerise target file** | `SELLERISE_RAW_DATA.json` | `SELLERISE_RAW_DATA_CA.json` present | `SELLERISE_RAW_DATA_UK.json` present | **MISSING** — no `SELLERISE_RAW_DATA_AU.json` | **BLOCKER for AU rollout** — cannot reconcile AU until Sellerise target file is provided |
| **Unmapped leaves after US classify()** | 0 (locked design) | 2 leaves: `Refund.DigitalServicesFee` (+$0.54) + `Shipment.Tax` (−$1.32, tiny CA-only) | 5 leaves: `Shipment.DigitalServicesFee`, `Shipment.DigitalServicesFeeFBA`, `Refund.DigitalServicesFee`, `Shipment.ShippingTaxDiscount`, `Refund.ShippingTaxDiscount` | 3 leaves: `Shipment.Tax` (−$105), `Shipment.ShippingTaxDiscount` (−$3.38), `ServiceFee.Promo` (+$5.25) | **MAP** — cover the ≤ 5 new leaves per marketplace; expected classifications listed per row above |

## Summary — what to build for rollout

**Config-only changes** (no logic delta, just add per-marketplace data
plumbing):

- Per-marketplace COGS workbook sheet is already selected by
  `MARKETPLACE_TO_SHEET`.
- Per-marketplace currency filter in `ad_spend_daily` load
  (`budget_currency = 'CAD' / 'GBP' / 'AUD'`).
- Per-marketplace Sellerise target path (already differentiated by suffix).
- No new SP-API refresh tokens (`EU`/`FE` already in `.env`), no new Ads token.

**Mapping/logic changes** (touch `bucket_map.py`):

| new rule | rationale | affects |
|---|---|---|
| `("Shipment", "DigitalServicesFee", *)` → `feesObject.DigitalServicesFee` (status split) | UK (and future EU) | UK Mar −$116; verified against Sellerise |
| `("Shipment", "DigitalServicesFeeFBA", *)` → `feesObject.DigitalServicesFeeFBA` (status split) | UK | tiny but present |
| `("Refund", "DigitalServicesFee", *)` → `refundsObject.DigitalServicesFee` (positive = refund) | UK, CA | matches Sellerise's refundsObject.DigitalServicesFee |
| `("Shipment", "ShippingTaxDiscount", *)` → `chargesObject.ShippingTax` (part of the tax pair) | UK, AU | UK −$18.74, AU −$3.38; treat as tax-side discount |
| `("Refund", "ShippingTaxDiscount", *)` → `refundsObject.ShippingTax` | UK | +$1.71 Mar |
| `("Shipment", "Tax", *)` → `passthrough` (GST family, mirrors MFT rule for AU/CA) | CA (tiny), AU | AU −$105 Mar — verify with AU Sellerise target when provided |
| `("Refund", "Tax", *)` → `refundsObject.Tax` (if it appears) | AU | probe next month for AU refund tax leaf |
| Add MarketplaceFacilitatorVAT-Principal/-Shipping to `_REFUND_TAX_WITHHELD_TYPES` | UK | Sellerise UK refundsObject has `Tax Withheld` — needs VAT variants routed there |

**Deferred until more data / a Sellerise target**:

- **AU rollout blocked** on missing `SELLERISE_RAW_DATA_AU.json`. Structural
  probe is done; reconciliation requires the target.
- UK `other-transaction` and UK `storageFee = 0` in May/Jun — needs a UK
  May/Jun `listTransactions` pull to identify the SP-API leaf.
- Per-marketplace refund + refund-COGS basis test — mirrors US methodology,
  requires per-marketplace Orders API sweep first.

## Evidence artifacts

- Raw per-marketplace transaction JSON:
  [rollout_probe/CA_2026-03_transactions.json](rollout_probe/CA_2026-03_transactions.json),
  [rollout_probe/UK_2026-03_transactions.json](rollout_probe/UK_2026-03_transactions.json),
  [rollout_probe/AU_2026-03_transactions.json](rollout_probe/AU_2026-03_transactions.json)
- Sellerise per-marketplace responses:
  [SELLERISE_RAW_DATA_CA.json](SELLERISE_RAW_DATA_CA.json),
  [SELLERISE_RAW_DATA_UK.json](SELLERISE_RAW_DATA_UK.json)

No US code, mapping, attribution, or accepted reconciliation number was
changed by this task. The differences matrix is the deliverable; nothing was
built.
