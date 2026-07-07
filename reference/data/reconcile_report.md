# Reconciliation report — marketplace ATVPDKIKX0DER

Generated 2026-07-06 12:34:23Z.
Trailing (DEFERRED-estimate) month: **2026-06**.
Tolerance: ±$0.01. Status legend: PASS · FAIL · EXPECTED (trailing-month estimate).

## Summary

- **PASS**: 32 / 162
- **FAIL**: 122 / 162
- **EXPECTED**: 2 / 162
- **OURS_MISSING**: 6 / 162

## Attribution basis

Shipment revenue + nested fees + `cog` re-attributed to **order PurchaseDate**
(from `order_purchase_date`). Non-order transactions stay on `postedDate`.
Refund basis chosen empirically: **postedDate** (refundsObject Σ|Δ|: posted-basis $1,699.51, purchase-basis $10,332.00).

**Before → After improvement** (`chargesObject.Principal` + `feesObject.Commission` + `fbaObject.FBAPerUnitFulfillmentFee` + `cog`):
- Σ|Δ| before (all `postedDate`): **$39,659.85**
- Σ|Δ| after  (Shipment on `PurchaseDate`): **$13,119.63**
- Reduction: **$26,540.22** (+66.9%)

- Cumulative Jan–Jun `net` delta before: **$+110,675.86** (+52.83% of Sellerise net)
- Cumulative Jan–Jun `net` delta after:  **$+108,509.97** (+51.80% of Sellerise net)

## Before / After (per key bucket per month)

| month | cell | before (ours) | after (ours) | Sellerise | Δ before | Δ after |
|---|---|---:|---:|---:|---:|---:|
| 2026-01 | `chargesObject.Principal` |   160,030.19 |   166,439.37 |   167,137.89 |    -7,107.70 |      -698.52 |
| 2026-01 | `feesObject.Commission` |   -23,616.21 |   -24,600.97 |   -24,709.34 |     1,093.13 |       108.37 |
| 2026-01 | `fbaObject.FBAPerUnitFulfillmentFee` |   -15,867.17 |   -16,497.25 |   -16,558.03 |       690.86 |        60.78 |
| 2026-01 | `cog` |    44,755.84 |    46,756.14 |    45,968.20 |    -1,212.36 |       787.94 |
| 2026-01 | `net` |    61,112.66 |    64,060.83 |    34,059.22 |    27,053.44 |    30,001.61 |
| 2026-02 | `chargesObject.Principal` |   144,947.88 |   137,786.86 |   136,806.23 |     8,141.65 |       980.63 |
| 2026-02 | `feesObject.Commission` |   -21,714.04 |   -20,639.83 |   -20,490.89 |    -1,223.15 |      -148.94 |
| 2026-02 | `fbaObject.FBAPerUnitFulfillmentFee` |   -14,036.62 |   -13,277.46 |   -13,075.82 |      -960.80 |      -201.64 |
| 2026-02 | `cog` |    39,032.01 |    36,414.64 |    34,647.26 |     4,384.75 |     1,767.38 |
| 2026-02 | `net` |    60,039.74 |    57,330.81 |    35,557.95 |    24,481.79 |    21,772.86 |
| 2026-03 | `chargesObject.Principal` |   124,499.06 |   122,342.47 |   121,824.06 |     2,675.00 |       518.41 |
| 2026-03 | `feesObject.Commission` |   -18,645.28 |   -18,324.02 |   -18,246.12 |      -399.16 |       -77.90 |
| 2026-03 | `fbaObject.FBAPerUnitFulfillmentFee` |   -10,991.16 |   -10,940.79 |   -10,942.68 |       -48.48 |         1.89 |
| 2026-03 | `cog` |    31,443.07 |    31,183.77 |    29,423.96 |     2,019.11 |     1,759.81 |
| 2026-03 | `net` |    54,257.84 |    52,746.85 |    35,435.13 |    18,822.71 |    17,311.72 |
| 2026-04 | `chargesObject.Principal` |   118,624.58 |   118,226.96 |   117,555.08 |     1,069.50 |       671.88 |
| 2026-04 | `feesObject.Commission` |   -17,783.19 |   -17,722.99 |   -17,622.34 |      -160.85 |      -100.65 |
| 2026-04 | `fbaObject.FBAPerUnitFulfillmentFee` |   -11,368.69 |   -11,246.70 |   -11,298.00 |       -70.69 |        51.30 |
| 2026-04 | `cog` |    32,356.34 |    32,151.26 |    30,790.78 |     1,565.56 |     1,360.48 |
| 2026-04 | `net` |    52,298.16 |    52,284.13 |    40,313.13 |    11,985.03 |    11,971.00 |
| 2026-05 | `chargesObject.Principal` |   108,811.83 |   109,289.49 |   110,260.80 |    -1,448.97 |      -971.31 |
| 2026-05 | `feesObject.Commission` |   -16,303.67 |   -16,321.33 |   -16,464.03 |       160.36 |       142.70 |
| 2026-05 | `fbaObject.FBAPerUnitFulfillmentFee` |   -10,462.84 |   -10,448.69 |   -10,548.50 |        85.66 |        99.81 |
| 2026-05 | `cog` |    27,923.18 |    28,241.87 |    27,180.01 |       743.17 |     1,061.86 |
| 2026-05 | `net` |    47,992.03 |    48,063.55 |    33,879.82 |    14,112.21 |    14,183.73 |
| 2026-06 | `chargesObject.Principal` |   100,008.13 |    97,953.93 |    98,691.38 |     1,316.75 |      -737.45 |
| 2026-06 | `feesObject.Commission` |   -11,842.53 |   -10,788.93 |   -10,639.72 |    -1,202.81 |      -149.21 |
| 2026-06 | `fbaObject.FBAPerUnitFulfillmentFee` |    -7,810.12 |    -7,132.71 |    -7,065.53 |      -744.59 |       -67.18 |
| 2026-06 | `cog` |    26,425.77 |    25,884.57 |    25,290.98 |     1,134.79 |       593.59 |
| 2026-06 | `net` |    44,463.90 |    43,512.27 |    30,243.22 |    14,220.68 |    13,269.05 |

## Refund-basis empirical test

Sum of Refund transactions bucketed by `postedDate` vs `PurchaseDate`, per month.
Winner: **postedDate** (smaller Σ|Δ| against Sellerise's `refundsObject`).

| month | ours (posted) | ours (purchase) | Sellerise Σ | Δ posted | Δ purchase |
|---|---:|---:|---:|---:|---:|
| 2026-01 |    -9,644.40 |    -7,864.46 |    -9,617.42 |       -26.98 |     1,752.96 |
| 2026-02 |    -8,745.40 |    -7,806.49 |    -8,727.61 |       -17.79 |       921.12 |
| 2026-03 |    -7,795.65 |    -7,132.60 |    -7,631.16 |      -164.49 |       498.56 |
| 2026-04 |    -3,984.75 |    -4,565.87 |    -3,870.95 |      -113.80 |      -694.92 |
| 2026-05 |    -5,384.48 |    -4,549.27 |    -5,645.49 |       261.01 |     1,096.22 |
| 2026-06 |    -3,821.97 |    -1,793.79 |    -3,286.51 |      -535.46 |     1,492.72 |

## Locked validation targets (Step 3 assertions)

| Dec. | bucket · sub_line | month | expected | actual | delta | status |
|---|---|---|---:|---:|---:|---|
| A | `feesObject.ReferralFee` | 2026-02 |         0.00 |         0.00 |         0.00 | PASS |
| A | `feesObject.ReferralFee` | 2026-03 |         0.00 |         0.00 |         0.00 | PASS |
| A | `fbaObject.FBAFees` | 2026-02 |         0.00 |         0.00 |         0.00 | PASS |
| A | `fbaObject.FBAFees` | 2026-03 |         0.00 |         0.00 |         0.00 | PASS |
| D | `refundsObject.RestockingFee` | 2026-02 |        52.94 |        52.94 |         0.00 | PASS |
| D | `refundsObject.RestockingFee` | 2026-04 |         4.59 |         4.87 |         0.28 | FAIL |
| D | `refundsObject.RestockingFee` | 2026-06 |         9.70 |         9.70 |         0.00 | PASS |
| D | `refundsObject.Goodwill` | 2026-05 |       -17.09 |       -17.09 |         0.00 | PASS |
| D | `refundsObject.Goodwill` | 2026-06 |       -13.23 |       -13.23 |         0.00 | PASS |
| E | `refundsObject.Promotion` | 2026-02 |       146.99 |       146.99 |         0.00 | PASS |
| E | `refundsObject.Promotion` | 2026-03 |        44.87 |        46.87 |         2.00 | FAIL |
| E | `refundsObject.Promotion` | 2026-06 |         3.99 |         4.99 |         1.00 | FAIL |
| E | `chargesObject.Promotion` | 2026-02 |      -811.14 |      -819.10 |        -7.96 | FAIL |
| E | `chargesObject.Promotion` | 2026-03 |      -610.03 |      -613.51 |        -3.48 | FAIL |
| E | `chargesObject.Promotion` | 2026-06 |      -496.12 |      -505.04 |        -8.92 | FAIL |

**Locked targets: 9 / 15 PASS**

## Advertising audit cross-check (decision B)

SP-API `ProductAdsPayment.AdvertisingFee` monthly total vs Ads-API `totalCost` sum.
Informational: SP-API bills the money, Ads-API attributes it. Ads-side is Phase 4.

| month | SP-API AdvertisingFee | Ads-API total | delta |
|---|---:|---:|---:|
| 2026-01 |   -31,317.11 |         0.00 |   -31,317.11 |
| 2026-02 |   -23,361.46 |         0.00 |   -23,361.46 |
| 2026-03 |   -19,035.25 |         0.00 |   -19,035.25 |
| 2026-04 |   -13,226.65 |         0.00 |   -13,226.65 |
| 2026-05 |   -15,620.47 |         0.00 |   -15,620.47 |
| 2026-06 |   -15,104.16 |         0.00 |   -15,104.16 |

## 2026-01

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |        -0.00 |    31,369.26 |   -31,369.26 | OURS_MISSING |
| `chargesObject` | `GiftWrap` |         4.49 |         4.49 |         0.00 | PASS |
| `chargesObject` | `GiftWrapTax` |         0.31 |         0.31 |         0.00 | PASS |
| `chargesObject` | `Principal` |   166,439.37 |   167,137.89 |      -698.52 | FAIL |
| `chargesObject` | `Promotion` |    -2,019.31 |    -1,997.42 |       -21.89 | FAIL |
| `chargesObject` | `ShippingCharge` |       847.26 |       924.98 |       -77.72 | FAIL |
| `chargesObject` | `ShippingTax` |         5.20 |        13.82 |        -8.62 | FAIL |
| `chargesObject` | `Tax` |     9,027.50 |     9,107.87 |       -80.37 | FAIL |
| `cog` | `(scalar)` |    46,756.14 |    45,968.20 |       787.94 | FAIL |
| `expenses` | `(aggregate)` |   -10,288.49 |    -9,743.45 |      -545.04 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |   -16,497.25 |   -16,558.03 |        60.78 | FAIL |
| `feesObject` | `Commission` |   -24,600.97 |   -24,709.34 |       108.37 | FAIL |
| `feesObject` | `GiftwrapChargeback` |        -4.49 |        -4.49 |         0.00 | PASS |
| `feesObject` | `ShippingChargeback` |      -233.27 |      -309.52 |        76.25 | FAIL |
| `net` | `(derived)` |    64,060.83 |    34,059.22 |    30,001.61 | FAIL |
| `refundsObject` | `Commission` |     1,649.22 |     1,644.62 |         4.60 | FAIL |
| `refundsObject` | `Principal` |   -11,169.10 |   -11,138.44 |       -30.66 | FAIL |
| `refundsObject` | `Promotion` |       188.10 |       188.10 |         0.00 | PASS |
| `refundsObject` | `RefundCommission` |      -298.64 |      -297.72 |        -0.92 | FAIL |
| `refundsObject` | `ShippingCharge` |       -46.45 |       -46.80 |         0.35 | FAIL |
| `refundsObject` | `ShippingChargeback` |        32.47 |        32.82 |        -0.35 | FAIL |
| `refundsObject` | `ShippingTax` |        -0.42 |        -0.45 |         0.03 | FAIL |
| `refundsObject` | `Tax` |      -740.06 |      -741.17 |         1.11 | FAIL |
| `refundsObject` | `Tax Withheld` |       740.48 |       741.62 |        -1.14 | FAIL |
| `salesTaxes` | `(derived)` |     9,033.01 |     9,122.00 |       -88.99 | FAIL |
| `storageFee` | `(scalar)` |     3,474.46 |     3,474.46 |         0.00 | PASS |

## 2026-02

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |        -0.00 |    22,929.02 |   -22,929.02 | OURS_MISSING |
| `chargesObject` | `Principal` |   137,786.86 |   136,806.23 |       980.63 | FAIL |
| `chargesObject` | `Promotion` |      -819.10 |      -811.14 |        -7.96 | FAIL |
| `chargesObject` | `ShippingCharge` |     1,035.68 |       956.45 |        79.23 | FAIL |
| `chargesObject` | `ShippingTax` |        14.58 |         6.63 |         7.95 | FAIL |
| `chargesObject` | `Tax` |     7,128.51 |     7,053.27 |        75.24 | FAIL |
| `cog` | `(scalar)` |    36,414.64 |    34,647.26 |     1,767.38 | FAIL |
| `expenses` | `(aggregate)` |     6,068.78 |     5,528.52 |       540.26 | FAIL |
| `fbaObject` | `FBAFees` |         0.00 |        -3.95 |         3.95 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |   -13,277.46 |   -13,075.82 |      -201.64 | FAIL |
| `feesObject` | `Commission` |   -20,639.83 |   -20,490.89 |      -148.94 | FAIL |
| `feesObject` | `ReferralFee` |         0.00 |        -2.99 |         2.99 | FAIL |
| `feesObject` | `ShippingChargeback` |      -392.73 |      -313.48 |       -79.25 | FAIL |
| `net` | `(derived)` |    57,330.81 |    35,557.95 |    21,772.86 | FAIL |
| `refundsObject` | `Commission` |     1,503.14 |     1,500.11 |         3.03 | FAIL |
| `refundsObject` | `Principal` |   -10,116.35 |   -10,096.14 |       -20.21 | FAIL |
| `refundsObject` | `Promotion` |       146.99 |       146.99 |         0.00 | PASS |
| `refundsObject` | `RefundCommission` |      -266.26 |      -265.65 |        -0.61 | FAIL |
| `refundsObject` | `RestockingFee` |        52.94 |        52.94 |         0.00 | PASS |
| `refundsObject` | `ShippingCharge` |      -162.91 |      -162.56 |        -0.35 | FAIL |
| `refundsObject` | `ShippingChargeback` |        97.05 |        96.70 |         0.35 | FAIL |
| `refundsObject` | `ShippingTax` |        -0.63 |        -0.60 |        -0.03 | FAIL |
| `refundsObject` | `Tax` |      -690.54 |      -688.92 |        -1.62 | FAIL |
| `refundsObject` | `Tax Withheld` |       691.17 |       689.52 |         1.65 | FAIL |
| `salesTaxes` | `(derived)` |     7,143.09 |     7,059.90 |        83.19 | FAIL |
| `storageFee` | `(scalar)` |     1,202.57 |     1,202.57 |         0.00 | PASS |

## 2026-03

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |        -0.00 |    18,792.62 |   -18,792.62 | OURS_MISSING |
| `chargesObject` | `GiftWrap` |         8.48 |         8.48 |         0.00 | PASS |
| `chargesObject` | `GiftWrapTax` |         0.78 |         0.78 |         0.00 | PASS |
| `chargesObject` | `Principal` |   122,342.47 |   121,824.06 |       518.41 | FAIL |
| `chargesObject` | `Promotion` |      -613.51 |      -610.03 |        -3.48 | FAIL |
| `chargesObject` | `ShippingCharge` |       692.90 |       681.44 |        11.46 | FAIL |
| `chargesObject` | `ShippingTax` |         2.88 |         2.21 |         0.67 | FAIL |
| `chargesObject` | `Tax` |     6,735.36 |     6,673.91 |        61.45 | FAIL |
| `cog` | `(scalar)` |    31,183.77 |    29,423.96 |     1,759.81 | FAIL |
| `expenses` | `(aggregate)` |    -2,096.10 |    -3,787.43 |     1,691.33 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |   -10,940.79 |   -10,942.68 |         1.89 | FAIL |
| `feesObject` | `Commission` |   -18,324.02 |   -18,246.12 |       -77.90 | FAIL |
| `feesObject` | `GiftwrapChargeback` |        -8.48 |        -8.48 |         0.00 | PASS |
| `feesObject` | `ShippingChargeback` |      -252.83 |      -245.85 |        -6.98 | FAIL |
| `net` | `(derived)` |    52,746.85 |    35,435.13 |    17,311.72 | FAIL |
| `refundsObject` | `Commission` |     1,333.93 |     1,305.88 |        28.05 | FAIL |
| `refundsObject` | `GiftWrap` |        -3.99 |        -3.99 |         0.00 | PASS |
| `refundsObject` | `GiftWrapTax` |        -0.32 |        -0.32 |         0.00 | PASS |
| `refundsObject` | `GiftwrapChargeback` |         3.99 |         3.99 |         0.00 | PASS |
| `refundsObject` | `Principal` |    -8,930.99 |    -8,741.99 |      -189.00 | FAIL |
| `refundsObject` | `Promotion` |        46.87 |        44.87 |         2.00 | FAIL |
| `refundsObject` | `RefundCommission` |      -236.78 |      -231.24 |        -5.54 | FAIL |
| `refundsObject` | `ShippingCharge` |       -17.07 |       -17.07 |         0.00 | PASS |
| `refundsObject` | `ShippingChargeback` |         8.39 |         8.39 |         0.00 | PASS |
| `refundsObject` | `ShippingTax` |        -0.67 |        -0.67 |         0.00 | PASS |
| `refundsObject` | `Tax` |      -583.02 |      -570.76 |       -12.26 | FAIL |
| `refundsObject` | `Tax Withheld` |       584.01 |       571.75 |        12.26 | FAIL |
| `salesTaxes` | `(derived)` |     6,739.02 |     6,676.90 |        62.12 | FAIL |
| `storageFee` | `(scalar)` |     1,177.95 |     1,177.95 |         0.00 | PASS |

## 2026-04

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |        -0.00 |    12,823.75 |   -12,823.75 | OURS_MISSING |
| `chargesObject` | `Principal` |   118,226.96 |   117,555.08 |       671.88 | FAIL |
| `chargesObject` | `Promotion` |      -515.66 |      -515.99 |         0.33 | FAIL |
| `chargesObject` | `ShippingCharge` |       733.93 |       735.26 |        -1.33 | FAIL |
| `chargesObject` | `ShippingTax` |        10.93 |        10.93 |         0.00 | PASS |
| `chargesObject` | `Tax` |     6,077.62 |     6,050.24 |        27.38 | FAIL |
| `cog` | `(scalar)` |    32,151.26 |    30,790.78 |     1,360.48 | FAIL |
| `expenses` | `(aggregate)` |    -6,120.81 |    -4,885.45 |    -1,235.36 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |   -11,246.70 |   -11,298.00 |        51.30 | FAIL |
| `feesObject` | `Commission` |   -17,722.99 |   -17,622.34 |      -100.65 | FAIL |
| `feesObject` | `ShippingChargeback` |      -284.57 |      -284.57 |         0.00 | PASS |
| `net` | `(derived)` |    52,284.13 |    40,313.13 |    11,971.00 | FAIL |
| `refundsObject` | `Commission` |       682.52 |       662.98 |        19.54 | FAIL |
| `refundsObject` | `Principal` |    -4,585.73 |    -4,457.43 |      -128.30 | FAIL |
| `refundsObject` | `Promotion` |        52.45 |        49.94 |         2.51 | FAIL |
| `refundsObject` | `RefundCommission` |      -121.90 |      -118.58 |        -3.32 | FAIL |
| `refundsObject` | `RestockingFee` |         4.87 |         4.59 |         0.28 | FAIL |
| `refundsObject` | `ShippingCharge` |       -25.87 |       -21.36 |        -4.51 | FAIL |
| `refundsObject` | `ShippingChargeback` |         8.91 |         8.91 |         0.00 | PASS |
| `refundsObject` | `ShippingTax` |        -0.67 |        -0.67 |         0.00 | PASS |
| `refundsObject` | `Tax` |      -276.22 |      -268.75 |        -7.47 | FAIL |
| `refundsObject` | `Tax Withheld` |       276.89 |       269.42 |         7.47 | FAIL |
| `salesTaxes` | `(derived)` |     6,088.55 |     6,061.17 |        27.38 | FAIL |
| `storageFee` | `(scalar)` |       770.83 |       770.83 |         0.00 | PASS |

## 2026-05

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |        -0.00 |    15,732.57 |   -15,732.57 | OURS_MISSING |
| `chargesObject` | `Principal` |   109,289.49 |   110,260.80 |      -971.31 | FAIL |
| `chargesObject` | `Promotion` |      -576.93 |      -584.52 |         7.59 | FAIL |
| `chargesObject` | `Shipping` |         0.00 |        36.62 |       -36.62 | FAIL |
| `chargesObject` | `ShippingCharge` |       859.78 |       837.74 |        22.04 | FAIL |
| `chargesObject` | `ShippingTax` |         2.63 |         2.63 |         0.00 | PASS |
| `chargesObject` | `Tax` |     5,513.37 |     5,584.90 |       -71.53 | FAIL |
| `cog` | `(scalar)` |    28,241.87 |    27,180.01 |     1,061.86 | FAIL |
| `expenses` | `(aggregate)` |    -3,623.80 |    -2,906.24 |      -717.56 | FAIL |
| `fbaObject` | `FBAFees` |       -29.64 |       -33.99 |         4.35 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |   -10,448.69 |   -10,548.50 |        99.81 | FAIL |
| `feesObject` | `Commission` |   -16,321.33 |   -16,464.03 |       142.70 | FAIL |
| `feesObject` | `POAServiceFee` |         0.00 |        -0.90 |         0.90 | FAIL |
| `feesObject` | `PoAPerUnitFulfillmentFee` |         0.00 |        -9.19 |         9.19 | FAIL |
| `feesObject` | `ReferralFee` |       -53.98 |       -56.97 |         2.99 | FAIL |
| `feesObject` | `ShippingChargeback` |      -397.04 |      -367.41 |       -29.63 | FAIL |
| `net` | `(derived)` |    48,063.55 |    33,879.82 |    14,183.73 | FAIL |
| `refundsObject` | `Commission` |       919.06 |       963.66 |       -44.60 | FAIL |
| `refundsObject` | `Goodwill` |       -17.09 |       -17.09 |         0.00 | PASS |
| `refundsObject` | `Principal` |    -6,126.90 |    -6,424.25 |       297.35 | FAIL |
| `refundsObject` | `Promotion` |        23.68 |        28.19 |        -4.51 | FAIL |
| `refundsObject` | `RefundCommission` |      -159.55 |      -167.81 |         8.26 | FAIL |
| `refundsObject` | `ShippingCharge` |       -70.32 |       -74.83 |         4.51 | FAIL |
| `refundsObject` | `ShippingChargeback` |        46.64 |        46.64 |         0.00 | PASS |
| `refundsObject` | `ShippingTax` |        -1.00 |        -1.00 |         0.00 | PASS |
| `refundsObject` | `Tax` |      -384.54 |      -403.65 |        19.11 | FAIL |
| `refundsObject` | `Tax Withheld` |       385.54 |       404.65 |       -19.11 | FAIL |
| `salesTaxes` | `(derived)` |     5,516.00 |     5,587.53 |       -71.53 | FAIL |
| `storageFee` | `(scalar)` |       631.76 |       631.76 |         0.00 | PASS |

## 2026-06 (trailing DEFERRED month)

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |        -0.00 |    15,049.63 |   -15,049.63 | OURS_MISSING |
| `chargesObject` | `Principal` |    97,953.93 |    98,691.38 |      -737.45 | FAIL |
| `chargesObject` | `Promotion` |      -505.04 |      -496.12 |        -8.92 | FAIL |
| `chargesObject` | `Shipping` |         0.00 |       174.08 |      -174.08 | FAIL |
| `chargesObject` | `ShippingCharge` |       587.10 |       397.11 |       189.99 | FAIL |
| `chargesObject` | `ShippingTax` |         6.47 |         6.47 |         0.00 | PASS |
| `chargesObject` | `Tax` |     4,904.21 |     4,901.27 |         2.94 | FAIL |
| `cog` | `(scalar)` |    25,884.57 |    25,290.98 |       593.59 | FAIL |
| `expenses` | `(aggregate)` |    -4,454.06 |    -4,603.20 |       149.14 | FAIL |
| `fbaObject` | `FBAFees` |    -2,388.38 |    -2,509.14 |       120.76 | EXPECTED |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |    -7,132.71 |    -7,065.53 |       -67.18 | FAIL |
| `feesObject` | `Commission` |   -10,788.93 |   -10,639.72 |      -149.21 | FAIL |
| `feesObject` | `ReferralFee` |    -3,882.89 |    -4,148.65 |       265.76 | EXPECTED |
| `feesObject` | `ShippingChargeback` |      -220.23 |      -129.03 |       -91.20 | FAIL |
| `net` | `(derived)` |    43,512.27 |    30,243.22 |    13,269.05 | FAIL |
| `refundsObject` | `Commission` |       653.28 |       561.72 |        91.56 | FAIL |
| `refundsObject` | `Goodwill` |       -13.23 |       -13.23 |         0.00 | PASS |
| `refundsObject` | `Principal` |    -4,357.32 |    -3,745.89 |      -611.43 | FAIL |
| `refundsObject` | `Promotion` |         4.99 |         3.99 |         1.00 | FAIL |
| `refundsObject` | `RefundCommission` |      -116.40 |       -99.81 |       -16.59 | FAIL |
| `refundsObject` | `RestockingFee` |         9.70 |         9.70 |         0.00 | PASS |
| `refundsObject` | `ShippingCharge` |       -67.25 |       -60.26 |        -6.99 | FAIL |
| `refundsObject` | `ShippingChargeback` |        64.26 |        57.27 |         6.99 | FAIL |
| `refundsObject` | `ShippingTax` |        -2.39 |        -2.02 |        -0.37 | FAIL |
| `refundsObject` | `Tax` |      -281.83 |      -243.21 |       -38.62 | FAIL |
| `refundsObject` | `Tax Withheld` |       284.22 |       245.23 |        38.99 | FAIL |
| `salesTaxes` | `(derived)` |     4,910.68 |     4,907.74 |         2.94 | FAIL |
| `storageFee` | `(scalar)` |       404.04 |       404.04 |         0.00 | PASS |
