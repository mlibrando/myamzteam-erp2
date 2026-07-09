# AU reconciliation vs Sellerboard

FX and content residuals are reported separately. A post-FX residual inside
the FX-granularity band is rate noise; outside it, it is content.

## Implied AUD->USD rate

Sellerboard converts per transaction date, so each family lands on its own
rate. The reference rate is set by refunds + ads, never by the buckets under
test. `|shipment - ref|` beyond the FX tolerance means shipment *content*
differs, not the rate (tolerance 0.02).

| month | reference rate | basis | shipment | refund | service | ads | \|ship-ref\| |
|---|---:|---|---:|---:|---:|---:|---:|
| 2026-01 | 0.6736 | refunds + ads | 0.5910 | 0.6735 | 0.6116 | 0.6790 | 0.0827 ⚠ |
| 2026-02 | 0.6957 | refunds + ads | 0.6896 | 0.6956 | 0.7005 | 0.7022 | 0.0061 |
| 2026-03 | 0.7038 | refunds + ads | 0.6767 | 0.7039 | 0.7014 | 0.6997 | 0.0271 ⚠ |
| 2026-04 | 0.6985 | refunds + ads | 0.7167 | 0.6984 | 0.6916 | 0.7083 | 0.0182 |
| 2026-05 | 0.7227 | refunds + ads | 0.7254 | 0.7304 | 0.7236 | 0.7183 | 0.0027 |
| 2026-06 | 0.6886 | all anchors (too few content-insensitive — rate weakly determined) | 0.6867 | — | 0.7064 | 0.7036 | 0.0019 |

Median reference rate: **0.6971** (workbook states 0.67).
⚠ marks a month whose shipment family cannot be reconciled to the reference
rate by any plausible intra-month FX move.

### Per-anchor implied rate (GST-normalised)

| anchor | 01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|
| `FBAfee / FBAPerUnitFulfillmentFee` | 0.6132 | 0.6715 | 0.6767 | 0.7168 | 0.7291 | 0.6857 |
| `ReferralFee / Commission` | 0.5910 | 0.6933 | 0.6776 | 0.7167 | 0.7254 | 0.6886 |
| `RefundedAmount / Refund.Principal` | 0.6735 | 0.6957 | 0.7038 | 0.6983 | 0.7380 | — |
| `RefundedReferralFee / Refund.Commission` | 0.6736 | 0.6955 | 0.7040 | 0.6985 | 0.7227 | — |
| `Storage / FBAStorageFee` | 0.6116 | 0.7005 | 0.7014 | 0.6916 | 0.7236 | 0.7064 |
| `advertising / ad_spend_daily` | 0.6790 | 0.7022 | 0.6997 | 0.7083 | 0.7183 | 0.7036 |
| `sales / Principal` | 0.5674 | 0.6896 | 0.6744 | 0.7096 | 0.7153 | 0.6867 |

## Per-bucket residuals

`ours` is AUD converted to USD at the month's reference rate. The FX band is
|ours_aud| x 0.02 (the widest residual a rate error alone can
produce), floored at $5.00 for Sellerboard's cent-rounding.

| month | bucket | ours (USD) | Sellerboard | post-FX Δ | Δ% | FX band | verdict |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-01 | `chargesObject.Revenue` | 9,247.30 | 7,788.70 | -1,458.60 | -15.77% | ±274.55 | **CONTENT** |
| 2026-01 | `feesObject.Commission` | -772.84 | -677.99 | +94.85 | +12.27% | ±22.95 | **CONTENT** |
| 2026-01 | `fbaObject.FBAPerUnitFulfillmentFee` | -834.49 | -759.57 | +74.92 | +8.98% | ±24.78 | **CONTENT** |
| 2026-01 | `storageFee.storageFee` | 572.70 | 519.95 | -52.75 | -9.21% | ±17.00 | **CONTENT** |
| 2026-01 | `refundsObject.Principal` | -1,350.36 | -1,350.04 | +0.32 | +0.02% | ±40.09 | FX noise |
| 2026-01 | `refundsObject.Commission` | 112.26 | 112.26 | -0.00 | -0.00% | ±5.00 | FX noise |
| 2026-02 | `chargesObject.Revenue` | 8,563.11 | 8,487.62 | -75.49 | -0.88% | ±246.17 | FX noise |
| 2026-02 | `feesObject.Commission` | -689.80 | -687.38 | +2.42 | +0.35% | ±19.83 | FX noise |
| 2026-02 | `fbaObject.FBAPerUnitFulfillmentFee` | -570.68 | -550.85 | +19.83 | +3.47% | ±16.41 | **CONTENT** |
| 2026-02 | `storageFee.storageFee` | 370.61 | 373.16 | +2.55 | +0.69% | ±10.65 | FX noise |
| 2026-02 | `refundsObject.Principal` | -141.92 | -141.92 | +0.00 | +0.00% | ±5.00 | FX noise |
| 2026-02 | `refundsObject.Commission` | 11.35 | 11.35 | -0.00 | -0.04% | ±5.00 | FX noise |
| 2026-03 | `chargesObject.Revenue` | 6,521.45 | 6,249.12 | -272.33 | -4.18% | ±185.32 | **CONTENT** |
| 2026-03 | `feesObject.Commission` | -516.73 | -497.50 | +19.23 | +3.72% | ±14.68 | **CONTENT** |
| 2026-03 | `fbaObject.FBAPerUnitFulfillmentFee` | -360.28 | -346.39 | +13.89 | +3.85% | ±10.24 | **CONTENT** |
| 2026-03 | `storageFee.storageFee` | 346.26 | 345.07 | -1.19 | -0.34% | ±9.84 | FX noise |
| 2026-03 | `refundsObject.Principal` | -332.31 | -332.31 | +0.00 | +0.00% | ±9.44 | FX noise |
| 2026-03 | `refundsObject.Commission` | 26.58 | 26.59 | +0.01 | +0.03% | ±5.00 | FX noise |
| 2026-04 | `chargesObject.Revenue` | 6,664.69 | 6,770.19 | +105.50 | +1.58% | ±190.82 | FX noise |
| 2026-04 | `feesObject.Commission` | -534.34 | -548.27 | -13.93 | -2.61% | ±15.30 | FX noise |
| 2026-04 | `fbaObject.FBAPerUnitFulfillmentFee` | -373.54 | -383.32 | -9.78 | -2.62% | ±10.70 | FX noise |
| 2026-04 | `storageFee.storageFee` | 321.82 | 318.61 | -3.21 | -1.00% | ±9.21 | FX noise |
| 2026-04 | `refundsObject.Principal` | -284.99 | -284.90 | +0.09 | +0.03% | ±8.16 | FX noise |
| 2026-04 | `refundsObject.Commission` | 22.80 | 22.80 | +0.00 | +0.00% | ±5.00 | FX noise |
| 2026-05 | `chargesObject.Revenue` | 6,886.50 | 6,816.53 | -69.97 | -1.02% | ±190.58 | FX noise |
| 2026-05 | `feesObject.Commission` | -557.02 | -559.13 | -2.11 | -0.38% | ±15.42 | FX noise |
| 2026-05 | `fbaObject.FBAPerUnitFulfillmentFee` | -406.66 | -410.27 | -3.61 | -0.89% | ±11.25 | FX noise |
| 2026-05 | `storageFee.storageFee` | 312.79 | 313.19 | +0.40 | +0.13% | ±8.66 | FX noise |
| 2026-05 | `refundsObject.Principal` | -940.47 | -960.46 | -19.99 | -2.13% | ±26.03 | FX noise |
| 2026-05 | `refundsObject.Commission` | 76.85 | 76.85 | +0.00 | +0.00% | ±5.00 | FX noise |
| 2026-06 | `chargesObject.Revenue` | 6,621.79 | 6,603.44 | -18.35 | -0.28% | ±192.32 | FX noise |
| 2026-06 | `feesObject.Commission` | -602.70 | -602.70 | -0.00 | -0.00% | ±17.50 | FX noise |
| 2026-06 | `fbaObject.FBAPerUnitFulfillmentFee` | -456.06 | -454.15 | +1.91 | +0.42% | ±13.25 | FX noise |
| 2026-06 | `storageFee.storageFee` | 285.64 | 293.02 | +7.38 | +2.58% | ±8.30 | FX noise |
| 2026-06 | `refundsObject.Principal` | 0.00 | 0.00 | +0.00 | +0.00% | ±5.00 | FX noise |
| 2026-06 | `refundsObject.Commission` | 0.00 | 0.00 | +0.00 | +0.00% | ±5.00 | FX noise |

**8 CONTENT flags** (post-FX residual beyond the FX band):

- 2026-01 chargesObject.Revenue -1,458.60
- 2026-01 feesObject.Commission +94.85
- 2026-01 fbaObject.FBAPerUnitFulfillmentFee +74.92
- 2026-01 storageFee.storageFee -52.75
- 2026-02 fbaObject.FBAPerUnitFulfillmentFee +19.83
- 2026-03 chargesObject.Revenue -272.33
- 2026-03 feesObject.Commission +19.23
- 2026-03 fbaObject.FBAPerUnitFulfillmentFee +13.89

## net, on Sellerboard's own basis

Rebuilt from our AUD lines using Sellerboard's formula, then converted. The
inventory-loss gap is added back because our cog matches `salesCosts`, so
without it we would be comparing a `salesCosts` net to a `productCosts` net.

| month | ours (USD) | Sellerboard netProfit | Δ | Δ% |
|---|---:|---:|---:|---:|
| 2026-01 | 1,864.59 | 1,152.00 | -712.59 | -61.86% |
| 2026-02 | 3,417.48 | 3,405.40 | -12.08 | -0.35% |
| 2026-03 | 2,964.02 | 2,764.04 | -199.98 | -7.24% |
| 2026-04 | 2,800.10 | 2,923.14 | +123.04 | +4.21% |
| 2026-05 | 2,623.51 | 2,477.99 | -145.52 | -5.87% |
| 2026-06 | 2,996.13 | 3,010.75 | +14.62 | +0.49% |
| **Σ** | | | **-932.50** | |

## cog (compared USD-to-USD; no FX on either side)

AU sheet is USD, Sellerboard is USD. Converting both by the same rate is a
no-op on the ratio, so cog is compared natively and the FX band does not apply.

| month | ours (USD) | salesCosts | Δ vs salesCosts | productCosts | inventory-loss gap |
|---|---:|---:|---:|---:|---:|
| 2026-01 | 3,136.09 | 3,016.45 | -119.64 | 3,160.90 | -144.45 |
| 2026-02 | 3,063.21 | 3,044.13 | -19.08 | 3,287.33 | -243.20 |
| 2026-03 | 2,019.66 | 2,050.65 | +30.99 | 2,168.35 | -117.70 |
| 2026-04 | 2,153.35 | 2,215.33 | +61.98 | 2,284.36 | -69.03 |
| 2026-05 | 1,942.68 | 2,174.11 | +231.43 | 2,205.10 | -30.99 |
| 2026-06 | 1,880.73 | 1,873.28 | -7.45 | 1,973.30 | -100.02 |
| **Σ** | | | **+178.23** | | **-705.39** |

## cog FX guard

- `GMAKER-3` = 30.9900 USD -> **44.45 AUD** at rate 0.6971 (expected 40..50) ✓
- inverted-conversion failure would give ~21.60 AUD
- double-conversion failure would give ~63.77 AUD
