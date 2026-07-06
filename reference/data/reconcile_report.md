# Reconciliation report — marketplace ATVPDKIKX0DER

Generated 2026-07-06 08:36:10Z.
Trailing (DEFERRED-estimate) month: **2026-06**.
Tolerance: ±$0.01. Status legend: PASS · FAIL · EXPECTED (trailing-month estimate).

## Summary

- **PASS**: 28 / 162
- **FAIL**: 126 / 162
- **EXPECTED**: 2 / 162
- **OURS_MISSING**: 6 / 162

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
| E | `chargesObject.Promotion` | 2026-02 |      -811.14 |      -816.15 |        -5.01 | FAIL |
| E | `chargesObject.Promotion` | 2026-03 |      -610.03 |      -669.25 |       -59.22 | FAIL |
| E | `chargesObject.Promotion` | 2026-06 |      -496.12 |      -517.35 |       -21.23 | FAIL |

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
| `chargesObject` | `Principal` |   160,030.19 |   167,137.89 |    -7,107.70 | FAIL |
| `chargesObject` | `Promotion` |    -2,135.60 |    -1,997.42 |      -138.18 | FAIL |
| `chargesObject` | `ShippingCharge` |       809.58 |       924.98 |      -115.40 | FAIL |
| `chargesObject` | `ShippingTax` |         5.18 |        13.82 |        -8.64 | FAIL |
| `chargesObject` | `Tax` |     8,588.44 |     9,107.87 |      -519.43 | FAIL |
| `cog` | `(scalar)` |    44,755.84 |    45,968.20 |    -1,212.36 | FAIL |
| `expenses` | `(aggregate)` |   -10,288.49 |    -9,743.45 |      -545.04 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |   -15,867.17 |   -16,558.03 |       690.86 | FAIL |
| `feesObject` | `Commission` |   -23,616.21 |   -24,709.34 |     1,093.13 | FAIL |
| `feesObject` | `GiftwrapChargeback` |        -4.49 |        -4.49 |         0.00 | PASS |
| `feesObject` | `ShippingChargeback` |      -233.43 |      -309.52 |        76.09 | FAIL |
| `net` | `(derived)` |    61,112.66 |    34,059.22 |    27,053.44 | FAIL |
| `refundsObject` | `Commission` |     1,649.22 |     1,644.62 |         4.60 | FAIL |
| `refundsObject` | `Principal` |   -11,169.10 |   -11,138.44 |       -30.66 | FAIL |
| `refundsObject` | `Promotion` |       188.10 |       188.10 |         0.00 | PASS |
| `refundsObject` | `RefundCommission` |      -298.64 |      -297.72 |        -0.92 | FAIL |
| `refundsObject` | `ShippingCharge` |       -46.45 |       -46.80 |         0.35 | FAIL |
| `refundsObject` | `ShippingChargeback` |        32.47 |        32.82 |        -0.35 | FAIL |
| `refundsObject` | `ShippingTax` |        -0.42 |        -0.45 |         0.03 | FAIL |
| `refundsObject` | `Tax` |      -740.06 |      -741.17 |         1.11 | FAIL |
| `refundsObject` | `Tax Withheld` |       740.48 |       741.62 |        -1.14 | FAIL |
| `salesTaxes` | `(derived)` |     8,593.93 |     9,122.00 |      -528.07 | FAIL |
| `storageFee` | `(scalar)` |     3,474.46 |     3,474.46 |         0.00 | PASS |

## 2026-02

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |        -0.00 |    22,929.02 |   -22,929.02 | OURS_MISSING |
| `chargesObject` | `Principal` |   144,947.88 |   136,806.23 |     8,141.65 | FAIL |
| `chargesObject` | `Promotion` |      -816.15 |      -811.14 |        -5.01 | FAIL |
| `chargesObject` | `ShippingCharge` |       956.79 |       956.45 |         0.34 | FAIL |
| `chargesObject` | `ShippingTax` |        14.84 |         6.63 |         8.21 | FAIL |
| `chargesObject` | `Tax` |     7,622.30 |     7,053.27 |       569.03 | FAIL |
| `cog` | `(scalar)` |    39,032.01 |    34,647.26 |     4,384.75 | FAIL |
| `expenses` | `(aggregate)` |     6,068.78 |     5,528.52 |       540.26 | FAIL |
| `fbaObject` | `FBAFees` |         0.00 |        -3.95 |         3.95 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |   -14,036.62 |   -13,075.82 |      -960.80 | FAIL |
| `feesObject` | `Commission` |   -21,714.04 |   -20,490.89 |    -1,223.15 | FAIL |
| `feesObject` | `ReferralFee` |         0.00 |        -2.99 |         2.99 | FAIL |
| `feesObject` | `ShippingChargeback` |      -318.14 |      -313.48 |        -4.66 | FAIL |
| `net` | `(derived)` |    60,039.74 |    35,557.95 |    24,481.79 | FAIL |
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
| `salesTaxes` | `(derived)` |     7,637.14 |     7,059.90 |       577.24 | FAIL |
| `storageFee` | `(scalar)` |     1,202.57 |     1,202.57 |         0.00 | PASS |

## 2026-03

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |        -0.00 |    18,792.62 |   -18,792.62 | OURS_MISSING |
| `chargesObject` | `GiftWrap` |         8.48 |         8.48 |         0.00 | PASS |
| `chargesObject` | `GiftWrapTax` |         0.78 |         0.78 |         0.00 | PASS |
| `chargesObject` | `Principal` |   124,499.06 |   121,824.06 |     2,675.00 | FAIL |
| `chargesObject` | `Promotion` |      -669.25 |      -610.03 |       -59.22 | FAIL |
| `chargesObject` | `ShippingCharge` |       782.86 |       681.44 |       101.42 | FAIL |
| `chargesObject` | `ShippingTax` |         2.91 |         2.21 |         0.70 | FAIL |
| `chargesObject` | `Tax` |     6,789.53 |     6,673.91 |       115.62 | FAIL |
| `cog` | `(scalar)` |    31,443.07 |    29,423.96 |     2,019.11 | FAIL |
| `expenses` | `(aggregate)` |    -2,096.10 |    -3,787.43 |     1,691.33 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |   -10,991.16 |   -10,942.68 |       -48.48 | FAIL |
| `feesObject` | `Commission` |   -18,645.28 |   -18,246.12 |      -399.16 | FAIL |
| `feesObject` | `GiftwrapChargeback` |        -8.48 |        -8.48 |         0.00 | PASS |
| `feesObject` | `ShippingChargeback` |      -301.72 |      -245.85 |       -55.87 | FAIL |
| `net` | `(derived)` |    54,257.84 |    35,435.13 |    18,822.71 | FAIL |
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
| `salesTaxes` | `(derived)` |     6,793.22 |     6,676.90 |       116.32 | FAIL |
| `storageFee` | `(scalar)` |     1,177.95 |     1,177.95 |         0.00 | PASS |

## 2026-04

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |        -0.00 |    12,823.75 |   -12,823.75 | OURS_MISSING |
| `chargesObject` | `Principal` |   118,624.58 |   117,555.08 |     1,069.50 | FAIL |
| `chargesObject` | `Promotion` |      -515.75 |      -515.99 |         0.24 | FAIL |
| `chargesObject` | `ShippingCharge` |       750.43 |       735.26 |        15.17 | FAIL |
| `chargesObject` | `ShippingTax` |        10.97 |        10.93 |         0.04 | FAIL |
| `chargesObject` | `Tax` |     6,106.80 |     6,050.24 |        56.56 | FAIL |
| `cog` | `(scalar)` |    32,356.34 |    30,790.78 |     1,565.56 | FAIL |
| `expenses` | `(aggregate)` |    -6,120.81 |    -4,885.45 |    -1,235.36 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |   -11,368.69 |   -11,298.00 |       -70.69 | FAIL |
| `feesObject` | `Commission` |   -17,783.19 |   -17,622.34 |      -160.85 | FAIL |
| `feesObject` | `ShippingChargeback` |      -297.30 |      -284.57 |       -12.73 | FAIL |
| `net` | `(derived)` |    52,298.16 |    40,313.13 |    11,985.03 | FAIL |
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
| `salesTaxes` | `(derived)` |     6,117.77 |     6,061.17 |        56.60 | FAIL |
| `storageFee` | `(scalar)` |       770.83 |       770.83 |         0.00 | PASS |

## 2026-05

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |        -0.00 |    15,732.57 |   -15,732.57 | OURS_MISSING |
| `chargesObject` | `Principal` |   108,811.83 |   110,260.80 |    -1,448.97 | FAIL |
| `chargesObject` | `Promotion` |      -572.56 |      -584.52 |        11.96 | FAIL |
| `chargesObject` | `Shipping` |         0.00 |        36.62 |       -36.62 | FAIL |
| `chargesObject` | `ShippingCharge` |       855.14 |       837.74 |        17.40 | FAIL |
| `chargesObject` | `ShippingTax` |         2.57 |         2.63 |        -0.06 | FAIL |
| `chargesObject` | `Tax` |     5,584.35 |     5,584.90 |        -0.55 | FAIL |
| `cog` | `(scalar)` |    27,923.18 |    27,180.01 |       743.17 | FAIL |
| `expenses` | `(aggregate)` |    -3,623.80 |    -2,906.24 |      -717.56 | FAIL |
| `fbaObject` | `FBAFees` |         0.00 |       -33.99 |        33.99 | FAIL |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |   -10,462.84 |   -10,548.50 |        85.66 | FAIL |
| `feesObject` | `Commission` |   -16,303.67 |   -16,464.03 |       160.36 | FAIL |
| `feesObject` | `POAServiceFee` |         0.00 |        -0.90 |         0.90 | FAIL |
| `feesObject` | `PoAPerUnitFulfillmentFee` |         0.00 |        -9.19 |         9.19 | FAIL |
| `feesObject` | `ReferralFee` |         0.00 |       -56.97 |        56.97 | FAIL |
| `feesObject` | `ShippingChargeback` |      -396.45 |      -367.41 |       -29.04 | FAIL |
| `net` | `(derived)` |    47,992.03 |    33,879.82 |    14,112.21 | FAIL |
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
| `salesTaxes` | `(derived)` |     5,586.92 |     5,587.53 |        -0.61 | FAIL |
| `storageFee` | `(scalar)` |       631.76 |       631.76 |         0.00 | PASS |

## 2026-06 (trailing DEFERRED month)

| bucket | sub_line | ours | theirs | delta | status |
|---|---|---:|---:|---:|---|
| `adExpenses` | `(aggregate)` |        -0.00 |    15,049.63 |   -15,049.63 | OURS_MISSING |
| `chargesObject` | `Principal` |   100,008.13 |    98,691.38 |     1,316.75 | FAIL |
| `chargesObject` | `Promotion` |      -517.35 |      -496.12 |       -21.23 | FAIL |
| `chargesObject` | `Shipping` |         0.00 |       174.08 |      -174.08 | FAIL |
| `chargesObject` | `ShippingCharge` |       640.47 |       397.11 |       243.36 | FAIL |
| `chargesObject` | `ShippingTax` |         6.00 |         6.47 |        -0.47 | FAIL |
| `chargesObject` | `Tax` |     4,805.08 |     4,901.27 |       -96.19 | FAIL |
| `cog` | `(scalar)` |    26,425.77 |    25,290.98 |     1,134.79 | FAIL |
| `expenses` | `(aggregate)` |    -4,454.06 |    -4,603.20 |       149.14 | FAIL |
| `fbaObject` | `FBAFees` |    -1,960.03 |    -2,509.14 |       549.11 | EXPECTED |
| `fbaObject` | `FBAPerUnitFulfillmentFee` |    -7,810.12 |    -7,065.53 |      -744.59 | FAIL |
| `feesObject` | `Commission` |   -11,842.53 |   -10,639.72 |    -1,202.81 | FAIL |
| `feesObject` | `ReferralFee` |    -3,136.60 |    -4,148.65 |     1,012.05 | EXPECTED |
| `feesObject` | `ShippingChargeback` |      -266.29 |      -129.03 |      -137.26 | FAIL |
| `net` | `(derived)` |    44,463.90 |    30,243.22 |    14,220.68 | FAIL |
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
| `salesTaxes` | `(derived)` |     4,811.08 |     4,907.74 |       -96.66 | FAIL |
| `storageFee` | `(scalar)` |       404.04 |       404.04 |         0.00 | PASS |
