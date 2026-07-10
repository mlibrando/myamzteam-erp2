# Reconciliation report — marketplace A1F83G8C2ARO7P

Generated 2026-07-10 06:03:49Z.
Trailing (DEFERRED-estimate) month: **2026-06**.
Tolerance: ±$0.01. Status legend: PASS · FAIL · EXPECTED (trailing-month estimate).

## Summary

- **PASS**: 85 / 164
- **FAIL**: 79 / 164

## Attribution basis

Shipment revenue + nested fees + `cog` re-attributed to **order PurchaseDate**
(from `order_purchase_date`). Non-order transactions stay on `postedDate`.
Refund basis chosen empirically: **postedDate** (refundsObject Σ|Δ|: posted-basis $407.08, purchase-basis $3,210.63).

**Before → After improvement** (`chargesObject.Principal` + `feesObject.Commission` + `fbaObject.FBAPerUnitFulfillmentFee` + `cog`):
- Σ|Δ| before (all `postedDate`): **$9,221.07**
- Σ|Δ| after  (Shipment on `PurchaseDate`): **$1,776.83**
- Reduction: **$7,444.24** (+80.7%)

- Cumulative Jan–Jun `net` delta before: **$-4,967.26** (-41.74% of Sellerise net)
- Cumulative Jan–Jun `net` delta after:  **$-1,593.57** (-13.39% of Sellerise net)

## Before / After (per key bucket per month)

| month | cell | before (ours) | after (ours) | Sellerise | Δ before | Δ after |
|---|---|---:|---:|---:|---:|---:|
| 2026-01 | `chargesObject.Principal` |    12,003.93 |    11,349.95 |    11,349.95 |       653.98 |         0.00 |
| 2026-01 | `feesObject.Commission` |    -2,143.63 |    -2,026.76 |    -1,873.48 |      -270.15 |      -153.28 |
| 2026-01 | `fbaObject.FBAPerUnitFulfillmentFee` |      -768.02 |      -745.57 |      -665.51 |      -102.51 |       -80.06 |
| 2026-01 | `cog` |     4,881.94 |     3,388.38 |     3,145.54 |     1,736.40 |       242.84 |
| 2026-01 | `net` |       348.76 |     1,334.59 |     1,632.00 |    -1,283.24 |      -297.41 |
| 2026-02 | `chargesObject.Principal` |    11,841.56 |    12,965.58 |    12,965.58 |    -1,124.02 |         0.00 |
| 2026-02 | `feesObject.Commission` |    -2,136.53 |    -2,338.84 |    -2,271.38 |       134.85 |       -67.46 |
| 2026-02 | `fbaObject.FBAPerUnitFulfillmentFee` |      -673.87 |      -712.87 |      -577.78 |       -96.09 |      -135.09 |
| 2026-02 | `cog` |     4,378.48 |     4,037.23 |     3,859.36 |       519.12 |       177.87 |
| 2026-02 | `net` |     1,406.50 |     2,625.69 |     2,941.74 |    -1,535.24 |      -316.05 |
| 2026-03 | `chargesObject.Principal` |    11,902.86 |    11,287.24 |    11,287.24 |       615.62 |         0.00 |
| 2026-03 | `feesObject.Commission` |    -2,142.25 |    -2,031.45 |    -1,979.75 |      -162.50 |       -51.70 |
| 2026-03 | `fbaObject.FBAPerUnitFulfillmentFee` |      -657.68 |      -628.38 |      -532.35 |      -125.33 |       -96.03 |
| 2026-03 | `cog` |     4,351.44 |     3,329.85 |     3,300.51 |     1,050.93 |        29.34 |
| 2026-03 | `net` |       936.11 |     1,484.94 |     1,597.00 |      -660.89 |      -112.06 |
| 2026-04 | `chargesObject.Principal` |    10,454.93 |     9,978.50 |     9,978.50 |       476.43 |         0.00 |
| 2026-04 | `feesObject.Commission` |    -1,881.61 |    -1,795.87 |    -1,795.87 |       -85.74 |         0.00 |
| 2026-04 | `fbaObject.FBAPerUnitFulfillmentFee` |      -479.28 |      -451.48 |      -391.13 |       -88.15 |       -60.35 |
| 2026-04 | `cog` |     4,052.00 |     3,479.54 |     3,295.13 |       756.87 |       184.41 |
| 2026-04 | `net` |     2,258.56 |     2,470.32 |     2,710.38 |      -451.82 |      -240.06 |
| 2026-05 | `chargesObject.Principal` |     5,501.07 |     5,358.57 |     5,358.57 |       142.50 |         0.00 |
| 2026-05 | `feesObject.Commission` |      -990.03 |      -964.38 |      -957.64 |       -32.39 |        -6.74 |
| 2026-05 | `fbaObject.FBAPerUnitFulfillmentFee` |      -262.29 |      -259.75 |      -195.45 |       -66.84 |       -64.30 |
| 2026-05 | `cog` |     1,980.96 |     1,767.62 |     1,645.00 |       335.96 |       122.62 |
| 2026-05 | `net` |       851.06 |       950.77 |     1,246.93 |      -395.87 |      -296.16 |
| 2026-06 | `chargesObject.Principal` |     6,869.23 |     6,853.44 |     6,853.44 |        15.79 |         0.00 |
| 2026-06 | `feesObject.Commission` |    -1,177.16 |    -1,174.32 |    -1,174.32 |        -2.84 |         0.00 |
| 2026-06 | `fbaObject.FBAPerUnitFulfillmentFee` |      -301.33 |      -298.39 |      -237.19 |       -64.14 |       -61.20 |
| 2026-06 | `cog` |     2,683.43 |     2,365.05 |     2,121.51 |       561.92 |       243.54 |
| 2026-06 | `net` |     1,131.38 |     1,439.75 |     1,771.58 |      -640.20 |      -331.83 |

## Refund-basis empirical test

Sum of Refund transactions bucketed by `postedDate` vs `PurchaseDate`, per month.
Winner: **postedDate** (smaller Σ|Δ| against Sellerise's `refundsObject`).

| month | ours (posted) | ours (purchase) | Sellerise Σ | Δ posted | Δ purchase |
|---|---:|---:|---:|---:|---:|
| 2026-01 |    -1,347.26 |    -1,884.38 |    -1,459.71 |       112.45 |      -424.67 |
| 2026-02 |    -1,157.91 |    -1,290.02 |    -1,124.17 |       -33.74 |      -165.85 |
| 2026-03 |    -1,848.89 |    -1,302.82 |    -1,846.25 |        -2.64 |       543.43 |
| 2026-04 |      -776.77 |      -753.36 |      -772.99 |        -3.78 |        19.63 |
| 2026-05 |      -604.63 |      -328.35 |      -563.88 |       -40.75 |       235.53 |
| 2026-06 |      -662.63 |      -537.67 |      -693.07 |        30.44 |       155.40 |

## Drift-guard: 5 INVESTIGATE / 4 KNOWN_TARGET_DEFECT / 30 TRAILING / 149 WITHIN_DRIFT

Regression guard per `DRIFT_BASELINE.md`. Trailing month: **2026-06**.
`WITHIN_DRIFT` = expected restatement drift · `TRAILING` = still moving (refund lag / DEFERRED) · `KNOWN_TARGET_DEFECT` = **diagnosed defect on the target's side, pinned to its measured Δ** · `INVESTIGATE` = **beyond the settled-month band, or a pinned defect that moved — possible pipeline regression**.

### 🔒 KNOWN_TARGET_DEFECT — our side is right; the target is wrong

Pinned, not excused: each cell must hold its measured Δ within a tight tolerance. If it moves in either direction — including toward zero, because the target fixed its bug — it fires `INVESTIGATE`.

| month | bucket · sub_line | Δ | expected Δ | tolerance (±) |
|---|---|---:|---:|---:|
| 2026-01 | `cog.(scalar)` |       242.84 |       242.84 |        25.00 |
| 2026-02 | `cog.(scalar)` |       177.87 |       177.87 |        25.00 |
| 2026-04 | `cog.(scalar)` |       184.41 |       184.41 |        25.00 |
| 2026-05 | `cog.(scalar)` |       122.62 |       122.62 |        25.00 |

- Sellerise understates UK per-SKU cost. Our workbook is validated against the component cost build-up (ABDB 78.53, GMAKER-3 30.94, MBUKB1 96.06 — all tie out to invoice); Sellerise's values do not. Do NOT edit the workbook; do NOT retune our cog to match. Measured aggregate Δ Jan–Jun = +$1,000.62, of which 2026-03 (+29.34) and 2026-06 (+243.54, trailing) sit inside their bands and are not pinned here. OPEN: the relayed per-SKU magnitudes (ABDB ~28%, MBUKB1 ~2%) do not reconcile with that aggregate — 28% on ABDB alone implies +$2,484.69 — and Sellerise exposes only monthly aggregate cog, so per-SKU cannot be confirmed from this repo. The classification rests on the build-up table; the magnitude is open with Elena.

### 🚨 INVESTIGATE — beyond settled-month band

| month | bucket · sub_line | Δ | band (±) |
|---|---|---:|---:|
| 2026-01 | `fbaObject.FBAPerUnitFulfillmentFee` |       -80.06 |        50.00 |
| 2026-02 | `fbaObject.FBAPerUnitFulfillmentFee` |      -135.09 |        50.00 |
| 2026-03 | `fbaObject.FBAPerUnitFulfillmentFee` |       -96.03 |        50.00 |
| 2026-04 | `fbaObject.FBAPerUnitFulfillmentFee` |       -60.35 |        50.00 |
| 2026-05 | `fbaObject.FBAPerUnitFulfillmentFee` |       -64.30 |        50.00 |

### Per-month summary

| month | WITHIN_DRIFT | TRAILING | KNOWN_TARGET_DEFECT | INVESTIGATE |
|---|---:|---:|---:|---:|
| 2026-01 | 33 | 0 | 1 | 1 |
| 2026-02 | 29 | 0 | 1 | 1 |
| 2026-03 | 32 | 0 | 0 | 1 |
| 2026-04 | 27 | 0 | 1 | 1 |
| 2026-05 | 28 | 0 | 1 | 1 |
| 2026-06 | 0 | 30 | 0 | 0 |

## Drift-guard vs prior pull: 0 INVESTIGATE / 30 TRAILING / 158 WITHIN_DRIFT

Prior pull: `2026-07-10T05:59:19.643185+00:00`. Current pull: `2026-07-10T06:03:49.079614+00:00`.
Bands per `DRIFT_VS_PRIOR_PULL.md` — tight, calibrated to observed pull-to-pull movement (baseline: $0.00 for ads over ~13h).

## Locked validation targets (Step 3 assertions)

| Dec. | bucket · sub_line | month | expected | actual | delta | status |
|---|---|---|---:|---:|---:|---|

**Locked targets: 0 / 0 PASS**

## Ad-lines reconciliation (Phase 4 Step 2c V1)

Ads-API `metric.totalCost` (USD-only, SB Video merged into SB) vs Sellerise's five `adExpenses` lines. Restatement drift up to ±$5.00 shows as `PASS_DRIFT` (small, expected — Amazon revises reports after Sellerise's snapshot). Trailing month is `EXPECTED_DRIFT`.

`as_of` timestamps per month: {'2026-06': '2026-07-07T08:29:09.567470+00:00', '2026-01': '2026-07-07T07:49:17.420406+00:00', '2026-02': '2026-07-07T07:49:21.027972+00:00', '2026-03': '2026-07-07T07:49:23.962940+00:00', '2026-05': '2026-07-07T08:29:14.293871+00:00', '2026-04': '2026-07-07T07:49:26.575112+00:00'}

| month | line | ours (USD) | Sellerise | Δ | status |
|---|---|---:|---:|---:|---|
| 2026-01 | adCost (Sponsored Products) |     1,638.58 |     1,638.58 |         0.00 | PASS |
| 2026-01 | hsaCost+hsaVideoCost (SB merged) |       469.19 |       469.19 |         0.00 | PASS |
| 2026-01 | sdCost (Sponsored Display) |        95.82 |        95.82 |         0.00 | PASS |
| 2026-01 | stvCost (Sponsored TV) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-01 | TOTAL |     2,203.59 |     2,203.59 |         0.00 | PASS |
| 2026-02 | adCost (Sponsored Products) |     1,711.72 |     1,711.72 |         0.00 | PASS |
| 2026-02 | hsaCost+hsaVideoCost (SB merged) |       144.70 |       144.70 |         0.00 | PASS |
| 2026-02 | sdCost (Sponsored Display) |        35.65 |        35.65 |         0.00 | PASS |
| 2026-02 | stvCost (Sponsored TV) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-02 | TOTAL |     1,892.07 |     1,892.07 |         0.00 | PASS |
| 2026-03 | adCost (Sponsored Products) |     1,639.07 |     1,639.07 |         0.00 | PASS |
| 2026-03 | hsaCost+hsaVideoCost (SB merged) |       127.66 |       127.66 |         0.00 | PASS |
| 2026-03 | sdCost (Sponsored Display) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-03 | stvCost (Sponsored TV) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-03 | TOTAL |     1,766.73 |     1,766.73 |         0.00 | PASS |
| 2026-04 | adCost (Sponsored Products) |       836.91 |       836.91 |         0.00 | PASS |
| 2026-04 | hsaCost+hsaVideoCost (SB merged) |        20.81 |        20.81 |         0.00 | PASS |
| 2026-04 | sdCost (Sponsored Display) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-04 | stvCost (Sponsored TV) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-04 | TOTAL |       857.72 |       857.72 |         0.00 | PASS |
| 2026-05 | adCost (Sponsored Products) |       699.16 |       699.16 |         0.00 | PASS |
| 2026-05 | hsaCost+hsaVideoCost (SB merged) |        12.08 |        12.08 |         0.00 | PASS |
| 2026-05 | sdCost (Sponsored Display) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-05 | stvCost (Sponsored TV) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-05 | TOTAL |       711.24 |       711.24 |         0.00 | PASS |
| 2026-06 | adCost (Sponsored Products) |       742.66 |       742.66 |         0.00 | PASS |
| 2026-06 | hsaCost+hsaVideoCost (SB merged) |         8.91 |         8.91 |         0.00 | PASS |
| 2026-06 | sdCost (Sponsored Display) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-06 | stvCost (Sponsored TV) |         0.00 |         0.00 |         0.00 | PASS |
| 2026-06 | TOTAL |       751.57 |       751.57 |         0.00 | PASS |

## Net before / after wiring `adExpenses` (Phase 4 Step 2c)

`net_before` = adExpenses set to 0; `net_after` = subtract real ad spend from Sellerise's formula.

| month | net_before (ours) | net_after (ours) | Sellerise net | Δ before | Δ after |
|---|---:|---:|---:|---:|---:|
| 2026-01 |     3,538.18 |     1,334.59 |     1,632.00 |     1,906.18 |      -297.41 |
| 2026-02 |     4,517.76 |     2,625.69 |     2,941.74 |     1,576.02 |      -316.05 |
| 2026-03 |     3,251.67 |     1,484.94 |     1,597.00 |     1,654.67 |      -112.06 |
| 2026-04 |     3,328.04 |     2,470.32 |     2,710.38 |       617.66 |      -240.06 |
| 2026-05 |     1,662.01 |       950.77 |     1,246.93 |       415.08 |      -296.16 |
| 2026-06 |     2,191.32 |     1,439.75 |     1,771.58 |       419.74 |      -331.83 |
| **Σ** | | | | **    6,589.35** | **   -1,593.57** |

## Advertising audit cross-check (decision B)

SP-API `ProductAdsPayment.AdvertisingFee` monthly total vs Ads-API `totalCost` sum.
Informational: SP-API bills the money, Ads-API attributes it. Ads-side is Phase 4.

| month | SP-API AdvertisingFee | Ads-API total | delta |
|---|---:|---:|---:|
| 2026-01 |    -2,504.09 |     2,203.59 |      -300.50 |
| 2026-02 |    -1,799.67 |     1,892.07 |        92.40 |
| 2026-03 |    -1,935.21 |     1,766.73 |      -168.48 |
| 2026-04 |      -790.71 |       857.72 |        67.01 |
| 2026-05 |      -792.75 |       711.24 |       -81.51 |
| 2026-06 |      -723.45 |       751.57 |        28.12 |

## 2026-01

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |     2,203.59 |     2,203.59 |         0.00 | PASS |
| `chargesObject` | `GiftWrap` |         2.49 |         2.49 |         0.00 | PASS |
| `chargesObject` | `GiftWrapTax` |         0.50 |         0.50 |         0.00 | PASS |
| `chargesObject` | `Principal` |    11,349.95 |    11,349.95 |         0.00 | PASS |
| `chargesObject` | `Promotion` |      -126.47 |      -151.35 |        24.88 | FAIL |
| `chargesObject` | `Shipping` |         0.00 |         2.50 |        -2.50 | FAIL |
| `chargesObject` | `ShippingCharge` |       156.44 |       154.36 |         2.08 | FAIL |
| `chargesObject` | `ShippingTax` |        12.31 |        12.31 |         0.00 | PASS |
| `chargesObject` | `Tax` |     2,115.01 |     2,115.01 |         0.00 | PASS |
| `cog` | `(scalar)` |     3,388.38 |     3,145.54 |       242.84 | FAIL |
| `expenses` | `(aggregate)` |       660.51 |       699.79 |       -39.28 | FAIL |
| `fbaObject` | `FBAFees` |         0.00 |        -8.71 |         8.71 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |      -745.57 |      -665.51 |       -80.06 | FAIL |
| `feesObject` | `Commission` |    -2,026.76 |    -1,873.48 |      -153.28 | FAIL |
| `feesObject` | `DigitalServicesFee` |       -52.02 |       -52.02 |         0.00 | PASS |
| `feesObject` | `GiftwrapChargeback` |        -2.49 |        -2.49 |         0.00 | PASS |
| `feesObject` | `ReferralFee` |         0.00 |       -35.23 |        35.23 | FAIL |
| `feesObject` | `ShippingChargeback` |      -102.93 |      -100.85 |        -2.08 | FAIL |
| `net` | `(derived)` |     1,334.59 |     1,632.00 |      -297.41 | FAIL |
| `refundsObject` | `Commission` |       277.24 |       262.18 |        15.06 | FAIL |
| `refundsObject` | `DigitalServicesFee` |         4.20 |         4.68 |        -0.48 | FAIL |
| `refundsObject` | `Principal` |    -1,564.35 |    -1,698.90 |       134.55 | FAIL |
| `refundsObject` | `Promotion` |        24.64 |        29.57 |        -4.93 | FAIL |
| `refundsObject` | `RefundCommission` |       -51.78 |       -56.62 |         4.84 | FAIL |
| `refundsObject` | `ShippingCharge` |        -1.45 |        -1.45 |         0.00 | PASS |
| `refundsObject` | `ShippingChargeback` |         0.83 |         0.83 |         0.00 | PASS |
| `refundsObject` | `ShippingTax` |        -0.30 |        -0.30 |         0.00 | PASS |
| `refundsObject` | `Tax` |      -312.90 |      -339.81 |        26.91 | FAIL |
| `refundsObject` | `Tax Withheld` |       276.61 |       340.11 |       -63.50 | FAIL |
| `salesTaxes` | `(derived)` |     2,127.82 |     2,127.82 |         0.00 | PASS |
| `storageFee` | `(scalar)` |       178.82 |       178.82 |         0.00 | PASS |

## 2026-02

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |     1,892.07 |     1,892.07 |         0.00 | PASS |
| `chargesObject` | `Principal` |    12,965.58 |    12,965.58 |         0.00 | PASS |
| `chargesObject` | `Promotion` |       -63.40 |       -76.21 |        12.81 | FAIL |
| `chargesObject` | `ShippingCharge` |       109.33 |       109.33 |         0.00 | PASS |
| `chargesObject` | `ShippingTax` |        20.10 |        20.10 |         0.00 | PASS |
| `chargesObject` | `Tax` |     2,467.06 |     2,467.06 |         0.00 | PASS |
| `cog` | `(scalar)` |     4,037.23 |     3,859.36 |       177.87 | FAIL |
| `expenses` | `(aggregate)` |     1,159.08 |     1,159.08 |         0.00 | PASS |
| `fbaObject` | `FBAFees` |         0.00 |       -17.84 |        17.84 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |      -712.87 |      -577.78 |      -135.09 | FAIL |
| `feesObject` | `Commission` |    -2,338.84 |    -2,271.38 |       -67.46 | FAIL |
| `feesObject` | `DigitalServicesFee` |       -55.82 |       -55.82 |         0.00 | PASS |
| `feesObject` | `ReferralFee` |         0.00 |       -67.46 |        67.46 | FAIL |
| `feesObject` | `ShippingChargeback` |       -44.35 |       -44.35 |         0.00 | PASS |
| `net` | `(derived)` |     2,625.69 |     2,941.74 |      -316.05 | FAIL |
| `refundsObject` | `Commission` |       237.17 |       237.17 |         0.00 | PASS |
| `refundsObject` | `DigitalServicesFee` |         5.49 |         5.49 |         0.00 | PASS |
| `refundsObject` | `Principal` |    -1,317.74 |    -1,317.74 |         0.00 | PASS |
| `refundsObject` | `Promotion` |         5.19 |         6.23 |        -1.04 | FAIL |
| `refundsObject` | `RefundCommission` |       -43.78 |       -43.78 |         0.00 | PASS |
| `refundsObject` | `ShippingCharge` |       -48.82 |       -48.82 |         0.00 | PASS |
| `refundsObject` | `ShippingChargeback` |        37.28 |        37.28 |         0.00 | PASS |
| `refundsObject` | `ShippingTax` |        -2.15 |        -2.15 |         0.00 | PASS |
| `refundsObject` | `Tax` |      -231.93 |      -231.93 |         0.00 | PASS |
| `refundsObject` | `Tax Withheld` |       201.38 |       234.08 |       -32.70 | FAIL |
| `salesTaxes` | `(derived)` |     2,487.16 |     2,487.16 |         0.00 | PASS |
| `storageFee` | `(scalar)` |       146.73 |       146.73 |         0.00 | PASS |

## 2026-03

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |     1,766.73 |     1,766.73 |         0.00 | PASS |
| `chargesObject` | `Principal` |    11,287.24 |    11,287.24 |         0.00 | PASS |
| `chargesObject` | `Promotion` |       -42.27 |       -49.46 |         7.19 | FAIL |
| `chargesObject` | `Shipping` |         0.00 |         0.86 |        -0.86 | FAIL |
| `chargesObject` | `ShippingCharge` |       139.50 |       138.67 |         0.83 | FAIL |
| `chargesObject` | `ShippingTax` |        26.03 |        25.89 |         0.14 | FAIL |
| `chargesObject` | `Tax` |     2,201.16 |     2,201.16 |         0.00 | PASS |
| `cog` | `(scalar)` |     3,329.85 |     3,300.51 |        29.34 | FAIL |
| `expenses` | `(aggregate)` |       383.93 |       370.19 |        13.74 | FAIL |
| `fbaObject` | `FBAFees` |         0.00 |        -8.93 |         8.93 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |      -628.38 |      -532.35 |       -96.03 | FAIL |
| `feesObject` | `Commission` |    -2,031.45 |    -1,979.75 |       -51.70 | FAIL |
| `feesObject` | `DigitalServicesFee` |       -49.48 |       -49.48 |         0.00 | PASS |
| `feesObject` | `DigitalServicesFeeFBA` |        -0.06 |        -0.06 |         0.00 | PASS |
| `feesObject` | `ReferralFee` |         0.00 |       -51.70 |        51.70 | FAIL |
| `feesObject` | `ShippingChargeback` |       -96.61 |       -96.47 |        -0.14 | FAIL |
| `net` | `(derived)` |     1,484.94 |     1,597.00 |      -112.06 | FAIL |
| `refundsObject` | `Commission` |       391.64 |       391.64 |         0.00 | PASS |
| `refundsObject` | `DigitalServicesFee` |         7.83 |         7.83 |         0.00 | PASS |
| `refundsObject` | `Principal` |    -2,175.97 |    -2,175.97 |         0.00 | PASS |
| `refundsObject` | `Promotion` |         6.60 |         7.92 |        -1.32 | FAIL |
| `refundsObject` | `RefundCommission` |       -71.07 |       -71.07 |         0.00 | PASS |
| `refundsObject` | `ShippingCharge` |        -7.12 |        -7.12 |         0.00 | PASS |
| `refundsObject` | `ShippingChargeback` |         0.52 |         0.52 |         0.00 | PASS |
| `refundsObject` | `ShippingTax` |        -1.42 |        -1.42 |         0.00 | PASS |
| `refundsObject` | `Tax` |      -435.25 |      -435.25 |         0.00 | PASS |
| `refundsObject` | `Tax Withheld` |       435.35 |       436.67 |        -1.32 | FAIL |
| `salesTaxes` | `(derived)` |     2,227.19 |     2,227.05 |         0.14 | FAIL |
| `storageFee` | `(scalar)` |       148.08 |       148.08 |         0.00 | PASS |

## 2026-04

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |       857.72 |       857.72 |         0.00 | PASS |
| `chargesObject` | `Principal` |     9,978.50 |     9,978.50 |         0.00 | PASS |
| `chargesObject` | `Promotion` |       -42.28 |       -50.76 |         8.48 | FAIL |
| `chargesObject` | `ShippingCharge` |        84.71 |        84.71 |         0.00 | PASS |
| `chargesObject` | `ShippingTax` |        15.22 |        15.22 |         0.00 | PASS |
| `chargesObject` | `Tax` |     1,966.85 |     1,966.85 |         0.00 | PASS |
| `cog` | `(scalar)` |     3,479.54 |     3,295.13 |       184.41 | FAIL |
| `expenses` | `(aggregate)` |     1,633.57 |     1,588.33 |        45.24 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |      -451.48 |      -391.13 |       -60.35 | FAIL |
| `feesObject` | `Commission` |    -1,795.87 |    -1,795.87 |         0.00 | PASS |
| `feesObject` | `DigitalServicesFee` |       -42.50 |       -42.50 |         0.00 | PASS |
| `feesObject` | `ShippingChargeback` |       -40.95 |       -40.95 |         0.00 | PASS |
| `net` | `(derived)` |     2,470.32 |     2,710.38 |      -240.06 | FAIL |
| `refundsObject` | `Commission` |       163.91 |       163.91 |         0.00 | PASS |
| `refundsObject` | `DigitalServicesFee` |         3.57 |         3.57 |         0.00 | PASS |
| `refundsObject` | `Principal` |      -916.33 |      -916.33 |         0.00 | PASS |
| `refundsObject` | `Promotion` |         9.49 |        11.38 |        -1.89 | FAIL |
| `refundsObject` | `RefundCommission` |       -28.85 |       -28.85 |         0.00 | PASS |
| `refundsObject` | `ShippingCharge` |       -22.06 |       -22.06 |         0.00 | PASS |
| `refundsObject` | `ShippingChargeback` |        15.39 |        15.39 |         0.00 | PASS |
| `refundsObject` | `ShippingTax` |        -1.05 |        -1.05 |         0.00 | PASS |
| `refundsObject` | `Tax` |      -119.95 |      -119.95 |         0.00 | PASS |
| `refundsObject` | `Tax Withheld` |       119.11 |       121.00 |        -1.89 | FAIL |
| `salesTaxes` | `(derived)` |     1,982.07 |     1,982.07 |         0.00 | PASS |
| `storageFee` | `(scalar)` |       105.78 |       105.78 |         0.00 | PASS |

## 2026-05

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |       711.24 |       711.24 |         0.00 | PASS |
| `chargesObject` | `Principal` |     5,358.57 |     5,358.57 |         0.00 | PASS |
| `chargesObject` | `Promotion` |       -36.07 |       -42.08 |         6.01 | FAIL |
| `chargesObject` | `ShippingCharge` |        61.53 |        61.53 |         0.00 | PASS |
| `chargesObject` | `ShippingTax` |        10.56 |        10.56 |         0.00 | PASS |
| `chargesObject` | `Tax` |     1,043.78 |     1,043.78 |         0.00 | PASS |
| `cog` | `(scalar)` |     1,767.62 |     1,645.00 |       122.62 | FAIL |
| `expenses` | `(aggregate)` |       -10.03 |       -73.89 |        63.86 | FAIL |
| `fbaObject` | `FBAFees` |         0.00 |        -3.10 |         3.10 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |      -259.75 |      -195.45 |       -64.30 | FAIL |
| `feesObject` | `Commission` |      -964.38 |      -957.64 |        -6.74 | FAIL |
| `feesObject` | `DigitalServicesFee` |       -23.04 |       -23.04 |         0.00 | PASS |
| `feesObject` | `ReferralFee` |         0.00 |        -6.74 |         6.74 | FAIL |
| `feesObject` | `ShippingChargeback` |       -25.00 |       -25.00 |         0.00 | PASS |
| `net` | `(derived)` |       950.77 |     1,246.93 |      -296.16 | FAIL |
| `refundsObject` | `Commission` |       126.22 |       119.48 |         6.74 | FAIL |
| `refundsObject` | `DigitalServicesFee` |         2.50 |         2.37 |         0.13 | FAIL |
| `refundsObject` | `Principal` |      -701.34 |      -663.88 |       -37.46 | FAIL |
| `refundsObject` | `Promotion` |         3.32 |         3.98 |        -0.66 | FAIL |
| `refundsObject` | `RefundCommission` |       -23.86 |       -22.51 |        -1.35 | FAIL |
| `refundsObject` | `ShippingCharge` |        -3.32 |        -3.32 |         0.00 | PASS |
| `refundsObject` | `ShippingTax` |        -0.66 |        -0.66 |         0.00 | PASS |
| `refundsObject` | `Tax` |      -140.27 |      -132.78 |        -7.49 | FAIL |
| `refundsObject` | `Tax Withheld` |       132.78 |       133.44 |        -0.66 | FAIL |
| `salesTaxes` | `(derived)` |     1,054.34 |     1,054.34 |         0.00 | PASS |
| `storageFee` | `(scalar)` |        77.60 |         0.00 |        77.60 | FAIL |

## 2026-06 (trailing DEFERRED month)

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |       751.57 |       751.57 |         0.00 | PASS |
| `chargesObject` | `Principal` |     6,853.44 |     6,853.44 |         0.00 | PASS |
| `chargesObject` | `Promotion` |       -21.22 |       -24.85 |         3.63 | FAIL |
| `chargesObject` | `ShippingCharge` |        43.29 |        43.29 |         0.00 | PASS |
| `chargesObject` | `ShippingTax` |         6.52 |         6.52 |         0.00 | PASS |
| `chargesObject` | `Tax` |     1,313.64 |     1,313.64 |         0.00 | PASS |
| `cog` | `(scalar)` |     2,365.05 |     2,121.51 |       243.54 | FAIL |
| `expenses` | `(aggregate)` |      -184.12 |      -133.86 |       -50.26 | FAIL |
| `fbaObject` | `FBAFees` |       -13.90 |       -13.90 |         0.00 | PASS |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |      -298.39 |      -237.19 |       -61.20 | FAIL |
| `feesObject` | `Commission` |    -1,174.32 |    -1,174.32 |         0.00 | PASS |
| `feesObject` | `DigitalServicesFee` |       -29.61 |       -28.13 |        -1.48 | FAIL |
| `feesObject` | `ReferralFee` |       -59.82 |       -59.82 |         0.00 | PASS |
| `feesObject` | `ShippingChargeback` |       -20.79 |       -20.79 |         0.00 | PASS |
| `net` | `(derived)` |     1,439.75 |     1,771.58 |      -331.83 | FAIL |
| `refundsObject` | `Commission` |       140.34 |       147.08 |        -6.74 | FAIL |
| `refundsObject` | `DigitalServicesFee` |         2.80 |         2.93 |        -0.13 | FAIL |
| `refundsObject` | `Principal` |      -779.74 |      -817.20 |        37.46 | FAIL |
| `refundsObject` | `Promotion` |         3.74 |         4.49 |        -0.75 | FAIL |
| `refundsObject` | `RefundCommission` |       -25.28 |       -26.63 |         1.35 | FAIL |
| `refundsObject` | `ShippingCharge` |        -3.74 |        -3.74 |         0.00 | PASS |
| `refundsObject` | `ShippingTax` |        -0.75 |        -0.75 |         0.00 | PASS |
| `refundsObject` | `Tax` |      -159.23 |      -166.72 |         7.49 | FAIL |
| `refundsObject` | `Tax Withheld` |       159.23 |       167.47 |        -8.24 | FAIL |
| `salesTaxes` | `(derived)` |     1,320.16 |     1,320.16 |         0.00 | PASS |
| `storageFee` | `(scalar)` |        59.68 |         0.00 |        59.68 | FAIL |
