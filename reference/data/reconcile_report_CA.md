# Reconciliation report — marketplace A2EUQ1WTGCTBG2

Generated 2026-07-11 05:58:39Z.
Trailing (DEFERRED-estimate) month: **2026-06**.
Tolerance: ±$0.01. Status legend: PASS · FAIL · EXPECTED (trailing-month estimate).

## Summary

- **PASS**: 69 / 119
- **FAIL**: 48 / 119
- **EXPECTED**: 2 / 119

## Attribution basis

Shipment revenue + nested fees + `cog` re-attributed to **order PurchaseDate**
(from `order_purchase_date`). Non-order transactions stay on `postedDate`.
Refund basis chosen empirically: **postedDate** (refundsObject Σ|Δ|: posted-basis $61.28, purchase-basis $1,866.58).

**Before → After improvement** (`chargesObject.Principal` + `feesObject.Commission` + `fbaObject.FBAPerUnitFulfillmentFee` + `cog`):
- Σ|Δ| before (all `postedDate`): **$3,505.26**
- Σ|Δ| after  (Shipment on `PurchaseDate`): **$1,708.10**
- Reduction: **$1,797.16** (+51.3%)

- Cumulative Jan–Jun `net` delta before: **$-2,089.59** (-19.50% of Sellerise net)
- Cumulative Jan–Jun `net` delta after:  **$-374.48** (-3.50% of Sellerise net)

## Before / After (per key bucket per month)

| month | cell | before (ours) | after (ours) | Sellerise | Δ before | Δ after |
|---|---|---:|---:|---:|---:|---:|
| 2026-01 | `chargesObject.Principal` |     9,482.03 |     9,584.03 |     9,559.08 |       -77.05 |        24.95 |
| 2026-01 | `feesObject.Commission` |    -1,413.20 |    -1,432.96 |    -1,429.22 |        16.02 |        -3.74 |
| 2026-01 | `fbaObject.FBAPerUnitFulfillmentFee` |    -1,289.90 |    -1,351.32 |    -1,303.57 |        13.67 |       -47.75 |
| 2026-01 | `cog` |     1,914.14 |     1,445.51 |     1,587.21 |       326.93 |      -141.70 |
| 2026-01 | `net` |     1,430.65 |     1,950.03 |     1,793.24 |      -362.59 |       156.79 |
| 2026-02 | `chargesObject.Principal` |     9,234.43 |     8,711.18 |     8,910.68 |       323.75 |      -199.50 |
| 2026-02 | `feesObject.Commission` |    -1,385.07 |    -1,306.61 |    -1,336.54 |       -48.53 |        29.93 |
| 2026-02 | `fbaObject.FBAPerUnitFulfillmentFee` |      -989.39 |      -861.58 |      -843.31 |      -146.08 |       -18.27 |
| 2026-02 | `cog` |     1,992.17 |     1,676.52 |     1,881.36 |       110.81 |      -204.84 |
| 2026-02 | `net` |     2,860.64 |     2,859.31 |     2,842.09 |        18.55 |        17.22 |
| 2026-03 | `chargesObject.Principal` |     8,737.30 |     8,866.85 |     8,667.35 |        69.95 |       199.50 |
| 2026-03 | `feesObject.Commission` |    -1,310.56 |    -1,330.00 |    -1,300.07 |       -10.49 |       -29.93 |
| 2026-03 | `fbaObject.FBAPerUnitFulfillmentFee` |      -836.54 |      -846.26 |      -854.71 |        18.17 |         8.45 |
| 2026-03 | `cog` |     1,900.86 |     1,622.51 |     1,454.84 |       446.02 |       167.67 |
| 2026-03 | `net` |     2,244.71 |     2,623.45 |     2,612.81 |      -368.10 |        10.64 |
| 2026-04 | `chargesObject.Principal` |     4,926.07 |     4,955.32 |     4,955.32 |       -29.25 |         0.00 |
| 2026-04 | `feesObject.Commission` |      -710.15 |      -714.53 |      -714.53 |         4.38 |         0.00 |
| 2026-04 | `fbaObject.FBAPerUnitFulfillmentFee` |      -510.20 |      -512.77 |      -502.18 |        -8.02 |       -10.59 |
| 2026-04 | `cog` |     1,045.81 |       643.95 |       653.28 |       392.53 |        -9.33 |
| 2026-04 | `net` |      -384.00 |        40.16 |        41.22 |      -425.22 |        -1.06 |
| 2026-05 | `chargesObject.Principal` |     6,683.90 |     6,455.15 |     6,455.15 |       228.75 |         0.00 |
| 2026-05 | `feesObject.Commission` |      -974.27 |      -939.96 |      -939.96 |       -34.31 |         0.00 |
| 2026-05 | `fbaObject.FBAPerUnitFulfillmentFee` |      -681.48 |      -661.48 |      -650.52 |       -30.96 |       -10.96 |
| 2026-05 | `cog` |     1,615.26 |     1,222.02 |       894.10 |       721.16 |       327.92 |
| 2026-05 | `net` |     1,163.97 |     1,382.77 |     1,721.49 |      -557.52 |      -338.72 |
| 2026-06 | `chargesObject.Principal` |     6,898.18 |     6,898.18 |     7,097.68 |      -199.50 |      -199.50 |
| 2026-06 | `feesObject.Commission` |      -920.47 |      -920.47 |      -920.47 |         0.00 |         0.00 |
| 2026-06 | `fbaObject.FBAPerUnitFulfillmentFee` |      -562.94 |      -562.94 |      -547.22 |       -15.72 |       -15.72 |
| 2026-06 | `cog` |     1,766.37 |     1,591.01 |     1,533.16 |       233.21 |        57.85 |
| 2026-06 | `net` |     1,307.78 |     1,483.14 |     1,702.49 |      -394.71 |      -219.35 |

## Refund-basis empirical test

Sum of Refund transactions bucketed by `postedDate` vs `PurchaseDate`, per month.
Winner: **postedDate** (smaller Σ|Δ| against Sellerise's `refundsObject`).

| month | ours (posted) | ours (purchase) | Sellerise Σ | Δ posted | Δ purchase |
|---|---:|---:|---:|---:|---:|
| 2026-01 |      -423.48 |      -555.23 |      -464.84 |        41.36 |       -90.39 |
| 2026-02 |      -288.05 |      -126.05 |      -288.05 |         0.00 |       162.00 |
| 2026-03 |    -1,010.36 |    -1,266.06 |    -1,010.36 |         0.00 |      -255.70 |
| 2026-04 |    -1,092.03 |    -1,000.52 |    -1,092.03 |         0.00 |        91.51 |
| 2026-05 |      -589.82 |      -213.02 |      -589.82 |         0.00 |       376.80 |
| 2026-06 |      -584.53 |      -529.13 |      -584.53 |         0.00 |        55.40 |

## Drift-guard: 0 INVESTIGATE / 0 DEFECT_REMEASURED / 0 KNOWN_TARGET_DEFECT / 21 TRAILING / 120 WITHIN_DRIFT

Regression guard per `DRIFT_BASELINE.md`. Trailing month: **2026-06**.
`WITHIN_DRIFT` = expected restatement drift · `TRAILING` = still moving (refund lag / DEFERRED) · `KNOWN_TARGET_DEFECT` = **diagnosed defect on the target's side, pinned to its measured Δ** · `DEFECT_REMEASURED` = **the pinned Δ moved, and rows ingested since the pin account for all of it — re-pin, do not investigate** · `INVESTIGATE` = **beyond the settled-month band, or a pinned defect that moved — possible pipeline regression**.

### Per-month summary

| month | WITHIN_DRIFT | TRAILING | KNOWN_TARGET_DEFECT | DEFECT_REMEASURED | INVESTIGATE |
|---|---:|---:|---:|---:|---:|
| 2026-01 | 26 | 0 | 0 | 0 | 0 |
| 2026-02 | 22 | 0 | 0 | 0 | 0 |
| 2026-03 | 26 | 0 | 0 | 0 | 0 |
| 2026-04 | 23 | 0 | 0 | 0 | 0 |
| 2026-05 | 23 | 0 | 0 | 0 | 0 |
| 2026-06 | 0 | 21 | 0 | 0 | 0 |

## Drift-guard vs prior pull: 0 INVESTIGATE / 21 TRAILING / 120 WITHIN_DRIFT

Prior pull: `2026-07-11T05:56:12.348501+00:00`. Current pull: `2026-07-11T05:58:39.232894+00:00`.
Bands per `DRIFT_VS_PRIOR_PULL.md` — tight, calibrated to observed pull-to-pull movement (baseline: $0.00 for ads over ~13h).

## Locked validation targets (Step 3 assertions)

| Dec. | bucket · sub_line | month | expected | actual | delta | status |
|---|---|---|---:|---:|---:|---|

**Locked targets: 0 / 0 PASS**

## Ad-lines reconciliation (Phase 4 Step 2c V1)

Ads-API `metric.totalCost` (USD-only, SB Video merged into SB) vs Sellerise's five `adExpenses` lines. Restatement drift up to ±$5.00 shows as `PASS_DRIFT` (small, expected — Amazon revises reports after Sellerise's snapshot). Trailing month is `EXPECTED_DRIFT`.

`as_of` timestamps per month: {'2026-06': '2026-07-07T08:29:09.567470+00:00', '2026-01': '2026-07-10T13:29:07.926811+00:00', '2026-02': '2026-07-10T13:15:56.339760+00:00', '2026-03': '2026-07-10T13:38:49.410856+00:00', '2026-05': '2026-07-10T13:57:27.288920+00:00', '2026-04': '2026-07-10T13:48:07.467034+00:00'}

| month | line | ours (USD) | Sellerise | Δ | status |
|---|---|---:|---:|---:|---|
| 2026-01 | adCost (Sponsored Products) |     2,262.10 |     2,262.10 |         0.00 | PASS |
| 2026-01 | hsaCost+hsaVideoCost (SB merged) |       643.19 |       643.19 |         0.00 | PASS |
| 2026-01 | sdCost (Sponsored Display) |        14.34 |        14.34 |         0.00 | PASS |
| 2026-01 | stvCost (Sponsored TV) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-01 | TOTAL |     2,919.63 |     2,919.63 |         0.00 | PASS |
| 2026-02 | adCost (Sponsored Products) |     1,251.92 |     1,251.92 |         0.00 | PASS |
| 2026-02 | hsaCost+hsaVideoCost (SB merged) |       291.64 |       291.64 |         0.00 | PASS |
| 2026-02 | sdCost (Sponsored Display) |         4.40 |         4.40 |         0.00 | PASS |
| 2026-02 | stvCost (Sponsored TV) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-02 | TOTAL |     1,547.96 |     1,547.96 |         0.00 | PASS |
| 2026-03 | adCost (Sponsored Products) |     1,153.55 |     1,153.55 |         0.00 | PASS |
| 2026-03 | hsaCost+hsaVideoCost (SB merged) |         2.58 |         2.58 |         0.00 | PASS |
| 2026-03 | sdCost (Sponsored Display) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-03 | stvCost (Sponsored TV) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-03 | TOTAL |     1,156.13 |     1,156.13 |         0.00 | PASS |
| 2026-04 | adCost (Sponsored Products) |     1,190.30 |     1,190.30 |         0.00 | PASS |
| 2026-04 | hsaCost+hsaVideoCost (SB merged) |         1.19 |         1.19 |         0.00 | PASS |
| 2026-04 | sdCost (Sponsored Display) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-04 | stvCost (Sponsored TV) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-04 | TOTAL |     1,191.49 |     1,191.49 |         0.00 | PASS |
| 2026-05 | adCost (Sponsored Products) |       929.35 |       929.35 |         0.00 | PASS |
| 2026-05 | hsaCost+hsaVideoCost (SB merged) |         0.60 |         0.60 |         0.00 | PASS |
| 2026-05 | sdCost (Sponsored Display) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-05 | stvCost (Sponsored TV) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-05 | TOTAL |       929.95 |       929.95 |         0.00 | PASS |
| 2026-06 | adCost (Sponsored Products) |       747.92 |       747.92 |         0.00 | PASS |
| 2026-06 | hsaCost+hsaVideoCost (SB merged) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-06 | sdCost (Sponsored Display) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-06 | stvCost (Sponsored TV) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-06 | TOTAL |       747.92 |       747.92 |         0.00 | PASS |

## Net before / after wiring `adExpenses` (Phase 4 Step 2c)

`net_before` = adExpenses set to 0; `net_after` = subtract real ad spend from Sellerise's formula.

| month | net_before (ours) | net_after (ours) | Sellerise net | Δ before | Δ after |
|---|---:|---:|---:|---:|---:|
| 2026-01 |     4,869.66 |     1,950.03 |     1,793.24 |     3,076.42 |       156.79 |
| 2026-02 |     4,407.27 |     2,859.31 |     2,842.09 |     1,565.18 |        17.22 |
| 2026-03 |     3,779.58 |     2,623.45 |     2,612.81 |     1,166.77 |        10.64 |
| 2026-04 |     1,231.65 |        40.16 |        41.22 |     1,190.43 |        -1.06 |
| 2026-05 |     2,312.72 |     1,382.77 |     1,721.49 |       591.23 |      -338.72 |
| 2026-06 |     2,231.06 |     1,483.14 |     1,702.49 |       528.57 |      -219.35 |
| **Σ** | | | | **    8,118.60** | **     -374.48** |

## Advertising audit cross-check (decision B)

SP-API `ProductAdsPayment.AdvertisingFee` monthly total vs Ads-API `totalCost` sum.
Informational: SP-API bills the money, Ads-API attributes it. Ads-side is Phase 4.

| month | SP-API AdvertisingFee | Ads-API total | delta |
|---|---:|---:|---:|
| 2026-01 |    -2,691.40 |     2,919.63 |       228.23 |
| 2026-02 |    -1,462.72 |     1,547.96 |        85.24 |
| 2026-03 |    -1,464.60 |     1,156.13 |      -308.47 |
| 2026-04 |      -241.29 |     1,191.49 |       950.20 |
| 2026-05 |      -691.93 |       929.95 |       238.02 |
| 2026-06 |      -917.20 |       747.92 |      -169.28 |

## 2026-01

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |     2,919.63 |     2,919.63 |         0.00 | PASS |
| `chargesObject` | `Principal` |     9,584.03 |     9,559.08 |        24.95 | FAIL |
| `chargesObject` | `Promotion` |       -77.08 |       -77.08 |         0.00 | PASS |
| `chargesObject` | `ShippingCharge` |       107.86 |       107.86 |         0.00 | PASS |
| `chargesObject` | `ShippingTax` |         1.56 |         1.56 |         0.00 | PASS |
| `chargesObject` | `Tax` |       889.10 |       889.10 |         0.00 | PASS |
| `cog` | `(scalar)` |     1,445.51 |     1,587.21 |      -141.70 | FAIL |
| `expenses` | `(aggregate)` |       196.10 |       196.37 |        -0.27 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |    -1,351.32 |    -1,303.57 |       -47.75 | FAIL |
| `feesObject` | `Commission` |    -1,432.96 |    -1,429.22 |        -3.74 | FAIL |
| `feesObject` | `ShippingChargeback` |       -60.71 |       -60.71 |         0.00 | PASS |
| `net` | `(derived)` |     1,950.03 |     1,793.24 |       156.79 | FAIL |
| `refundsObject` | `Commission` |        72.37 |        79.45 |        -7.08 | FAIL |
| `refundsObject` | `DigitalServicesFee` |         0.00 |         0.14 |        -0.14 | FAIL |
| `refundsObject` | `Principal` |      -518.85 |      -568.75 |        49.90 | FAIL |
| `refundsObject` | `Promotion` |        38.72 |        41.46 |        -2.74 | FAIL |
| `refundsObject` | `RefundCommission` |       -13.41 |       -14.83 |         1.42 | FAIL |
| `refundsObject` | `ShippingCharge` |        -2.31 |        -2.31 |         0.00 | PASS |
| `refundsObject` | `Tax` |       -36.43 |       -36.43 |         0.00 | PASS |
| `refundsObject` | `Tax Withheld` |        36.43 |        36.43 |         0.00 | PASS |
| `salesTaxes` | `(derived)` |       890.66 |       890.66 |         0.00 | PASS |
| `storageFee` | `(scalar)` |        31.17 |        31.44 |        -0.27 | FAIL |

## 2026-02

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |     1,547.96 |     1,547.96 |         0.00 | PASS |
| `chargesObject` | `Principal` |     8,711.18 |     8,910.68 |      -199.50 | FAIL |
| `chargesObject` | `Promotion` |       -46.34 |       -46.34 |         0.00 | PASS |
| `chargesObject` | `ShippingCharge` |        46.34 |        46.34 |         0.00 | PASS |
| `chargesObject` | `Tax` |       917.22 |       927.20 |        -9.98 | FAIL |
| `cog` | `(scalar)` |     1,676.52 |     1,881.36 |      -204.84 | FAIL |
| `expenses` | `(aggregate)` |        60.41 |        60.63 |        -0.22 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |      -861.58 |      -843.31 |       -18.27 | FAIL |
| `feesObject` | `Commission` |    -1,306.61 |    -1,336.54 |        29.93 | FAIL |
| `net` | `(derived)` |     2,859.31 |     2,842.09 |        17.22 | FAIL |
| `refundsObject` | `Commission` |        49.11 |        49.11 |         0.00 | PASS |
| `refundsObject` | `Principal` |      -357.35 |      -357.35 |         0.00 | PASS |
| `refundsObject` | `Promotion` |        29.93 |        29.93 |         0.00 | PASS |
| `refundsObject` | `RefundCommission` |        -9.74 |        -9.74 |         0.00 | PASS |
| `refundsObject` | `Tax` |       -37.67 |       -37.67 |         0.00 | PASS |
| `refundsObject` | `Tax Withheld` |        37.67 |        37.67 |         0.00 | PASS |
| `salesTaxes` | `(derived)` |       917.22 |       927.20 |        -9.98 | FAIL |
| `storageFee` | `(scalar)` |       171.15 |       171.37 |        -0.22 | FAIL |

## 2026-03

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |     1,156.13 |     1,156.13 |         0.00 | PASS |
| `chargesObject` | `Principal` |     8,866.85 |     8,667.35 |       199.50 | FAIL |
| `chargesObject` | `Promotion` |       -35.10 |       -35.10 |         0.00 | PASS |
| `chargesObject` | `ShippingCharge` |        64.31 |        64.31 |         0.00 | PASS |
| `chargesObject` | `ShippingTax` |         3.39 |         3.39 |         0.00 | PASS |
| `chargesObject` | `Tax` |       999.58 |       989.60 |         9.98 | FAIL |
| `cog` | `(scalar)` |     1,622.51 |     1,454.84 |       167.67 | FAIL |
| `expenses` | `(aggregate)` |       355.68 |       355.97 |        -0.29 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |      -846.26 |      -854.71 |         8.45 | FAIL |
| `feesObject` | `Commission` |    -1,330.00 |    -1,300.07 |       -29.93 | FAIL |
| `feesObject` | `ShippingChargeback` |       -29.21 |       -29.21 |         0.00 | PASS |
| `net` | `(derived)` |     2,623.45 |     2,612.81 |        10.64 | FAIL |
| `refundsObject` | `Commission` |       171.65 |       171.65 |         0.00 | PASS |
| `refundsObject` | `DigitalServicesFee` |         0.54 |         0.54 |         0.00 | PASS |
| `refundsObject` | `Goodwill` |        -9.09 |        -9.09 |         0.00 | PASS |
| `refundsObject` | `Principal` |    -1,164.21 |    -1,164.21 |         0.00 | PASS |
| `refundsObject` | `Promotion` |        19.95 |        19.95 |         0.00 | PASS |
| `refundsObject` | `RefundCommission` |       -29.20 |       -29.20 |         0.00 | PASS |
| `refundsObject` | `Tax` |      -151.72 |      -151.72 |         0.00 | PASS |
| `refundsObject` | `Tax Withheld` |       151.72 |       151.72 |         0.00 | PASS |
| `salesTaxes` | `(derived)` |     1,002.97 |       992.99 |         9.98 | FAIL |
| `storageFee` | `(scalar)` |       278.14 |       278.43 |        -0.29 | FAIL |

## 2026-04

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |     1,191.49 |     1,191.49 |         0.00 | PASS |
| `chargesObject` | `Principal` |     4,955.32 |     4,955.32 |         0.00 | PASS |
| `chargesObject` | `Promotion` |      -230.31 |      -230.31 |         0.00 | PASS |
| `chargesObject` | `ShippingCharge` |        38.82 |        38.82 |         0.00 | PASS |
| `chargesObject` | `Tax` |       442.10 |       442.10 |         0.00 | PASS |
| `cog` | `(scalar)` |       643.95 |       653.28 |        -9.33 | FAIL |
| `expenses` | `(aggregate)` |       148.73 |       148.93 |        -0.20 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |      -512.77 |      -502.18 |       -10.59 | FAIL |
| `feesObject` | `Commission` |      -714.53 |      -714.53 |         0.00 | PASS |
| `net` | `(derived)` |        40.16 |        41.22 |        -1.06 | FAIL |
| `refundsObject` | `Commission` |       187.07 |       187.07 |         0.00 | PASS |
| `refundsObject` | `Principal` |    -1,266.95 |    -1,266.95 |         0.00 | PASS |
| `refundsObject` | `Promotion` |        34.08 |        34.08 |         0.00 | PASS |
| `refundsObject` | `RefundCommission` |       -32.10 |       -32.10 |         0.00 | PASS |
| `refundsObject` | `ShippingCharge` |       -14.13 |       -14.13 |         0.00 | PASS |
| `refundsObject` | `Tax` |      -146.37 |      -146.37 |         0.00 | PASS |
| `refundsObject` | `Tax Withheld` |       146.37 |       146.37 |         0.00 | PASS |
| `salesTaxes` | `(derived)` |       442.10 |       442.10 |         0.00 | PASS |
| `storageFee` | `(scalar)` |       568.90 |       569.10 |        -0.20 | FAIL |

## 2026-05

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |       929.95 |       929.95 |         0.00 | PASS |
| `chargesObject` | `Principal` |     6,455.15 |     6,455.15 |         0.00 | PASS |
| `chargesObject` | `Promotion` |      -206.26 |      -206.26 |         0.00 | PASS |
| `chargesObject` | `ShippingCharge` |        17.70 |        17.70 |         0.00 | PASS |
| `chargesObject` | `Tax` |       542.98 |       542.98 |         0.00 | PASS |
| `cog` | `(scalar)` |     1,222.02 |       894.10 |       327.92 | FAIL |
| `expenses` | `(aggregate)` |       599.31 |       599.47 |        -0.16 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |      -661.48 |      -650.52 |       -10.96 | FAIL |
| `feesObject` | `Commission` |      -939.96 |      -939.96 |         0.00 | PASS |
| `net` | `(derived)` |     1,382.77 |     1,721.49 |      -338.72 | FAIL |
| `refundsObject` | `Commission` |       100.72 |       100.72 |         0.00 | PASS |
| `refundsObject` | `Principal` |      -731.40 |      -731.40 |         0.00 | PASS |
| `refundsObject` | `Promotion` |        65.75 |        65.75 |         0.00 | PASS |
| `refundsObject` | `RefundCommission` |       -18.99 |       -18.99 |         0.00 | PASS |
| `refundsObject` | `ShippingCharge` |        -5.90 |        -5.90 |         0.00 | PASS |
| `refundsObject` | `Tax` |       -57.37 |       -57.37 |         0.00 | PASS |
| `refundsObject` | `Tax Withheld` |        57.37 |        57.37 |         0.00 | PASS |
| `salesTaxes` | `(derived)` |       542.98 |       542.98 |         0.00 | PASS |
| `storageFee` | `(scalar)` |       540.59 |       540.75 |        -0.16 | FAIL |

## 2026-06 (trailing DEFERRED month)

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |       747.92 |       747.92 |         0.00 | PASS |
| `chargesObject` | `Principal` |     6,898.18 |     7,097.68 |      -199.50 | FAIL |
| `chargesObject` | `Promotion` |      -432.49 |      -432.49 |         0.00 | PASS |
| `chargesObject` | `Tax` |       797.49 |       823.43 |       -25.94 | FAIL |
| `cog` | `(scalar)` |     1,591.01 |     1,533.16 |        57.85 | FAIL |
| `expenses` | `(aggregate)` |       387.19 |       387.40 |        -0.21 | FAIL |
| `fbaObject` | `FBAFees` |       -40.00 |       -58.10 |        18.10 | EXPECTED |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |      -562.94 |      -547.22 |       -15.72 | FAIL |
| `feesObject` | `Commission` |      -920.47 |      -920.47 |         0.00 | PASS |
| `feesObject` | `ReferralFee` |       -49.42 |       -84.83 |        35.41 | EXPECTED |
| `net` | `(derived)` |     1,483.14 |     1,702.49 |      -219.35 | FAIL |
| `refundsObject` | `Commission` |       100.18 |       100.18 |         0.00 | PASS |
| `refundsObject` | `Principal` |      -690.70 |      -690.70 |         0.00 | PASS |
| `refundsObject` | `Promotion` |        22.88 |        22.88 |         0.00 | PASS |
| `refundsObject` | `RefundCommission` |       -16.89 |       -16.89 |         0.00 | PASS |
| `refundsObject` | `Tax` |       -58.18 |       -58.18 |         0.00 | PASS |
| `refundsObject` | `Tax Withheld` |        58.18 |        58.18 |         0.00 | PASS |
| `salesTaxes` | `(derived)` |       797.49 |       823.43 |       -25.94 | FAIL |
| `storageFee` | `(scalar)` |       486.26 |       486.47 |        -0.21 | FAIL |
