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
| 2026-01 | 0.6736 | refunds + ads | 0.7016 | 0.6735 | 0.6116 | 0.6790 | 0.0280 ⚠ |
| 2026-02 | 0.6957 | refunds + ads | 0.7070 | 0.6956 | 0.7005 | 0.7022 | 0.0112 |
| 2026-03 | 0.7038 | refunds + ads | 0.6980 | 0.7039 | 0.7014 | 0.6997 | 0.0058 |
| 2026-04 | 0.6985 | refunds + ads | 0.7167 | 0.6984 | 0.6916 | 0.7083 | 0.0182 |
| 2026-05 | 0.7227 | refunds + ads | 0.7162 | 0.7304 | 0.7236 | 0.7183 | 0.0065 |
| 2026-06 | 0.6965 | all anchors (too few content-insensitive — rate weakly determined) | 0.6964 | — | 0.7064 | 0.7036 | 0.0001 |

Median reference rate: **0.6975** (workbook states 0.67).
⚠ marks a month whose shipment family cannot be reconciled to the reference
rate by any plausible intra-month FX move.

### Per-anchor implied rate (GST-normalised)

| anchor | 01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|
| `FBAfee / FBAPerUnitFulfillmentFee` | 0.7016 | 0.7071 | 0.6981 | 0.7168 | 0.7162 | 0.6965 |
| `ReferralFee / Commission` | 0.7049 | 0.7070 | 0.6980 | 0.7167 | 0.7164 | 0.6964 |
| `RefundedAmount / Refund.Principal` | 0.6735 | 0.6957 | 0.7038 | 0.6983 | 0.7380 | — |
| `RefundedReferralFee / Refund.Commission` | 0.6736 | 0.6955 | 0.7040 | 0.6985 | 0.7227 | — |
| `Storage / FBAStorageFee` | 0.6116 | 0.7005 | 0.7014 | 0.6916 | 0.7236 | 0.7064 |
| `advertising / ad_spend_daily` | 0.6790 | 0.7022 | 0.6997 | 0.7083 | 0.7183 | 0.7036 |
| `sales / Principal` | 0.6852 | 0.7018 | 0.6945 | 0.7096 | 0.7098 | 0.6921 |

## Per-bucket residuals

`ours` is AUD converted to USD at the month's reference rate. The FX band is
|ours_aud| x 0.02 (the widest residual a rate error alone can
produce), floored at $5.00 for Sellerboard's cent-rounding.

| month | bucket | ours (USD) | Sellerboard | post-FX Δ | Δ% | FX band | verdict |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-01 | `chargesObject.Revenue` | 7,657.26 | 7,788.70 | +131.44 | +1.72% | ±227.34 | FX noise |
| 2026-01 | `feesObject.Commission` | -647.92 | -677.99 | -30.07 | -4.64% | ±19.24 | **CONTENT** |
| 2026-01 | `fbaObject.FBAPerUnitFulfillmentFee` | -729.30 | -759.57 | -30.27 | -4.15% | ±21.65 | **CONTENT** |
| 2026-01 | `storageFee.storageFee` | 572.70 | 519.95 | -52.75 | -9.21% | ±17.00 | **CONTENT** |
| 2026-01 | `refundsObject.Principal` | -1,350.36 | -1,350.04 | +0.32 | +0.02% | ±40.09 | FX noise |
| 2026-01 | `refundsObject.Commission` | 112.26 | 112.26 | -0.00 | -0.00% | ±5.00 | FX noise |
| 2026-02 | `chargesObject.Revenue` | 8,414.47 | 8,487.62 | +73.15 | +0.87% | ±241.89 | FX noise |
| 2026-02 | `feesObject.Commission` | -676.45 | -687.38 | -10.93 | -1.62% | ±19.45 | FX noise |
| 2026-02 | `fbaObject.FBAPerUnitFulfillmentFee` | -541.96 | -550.85 | -8.89 | -1.64% | ±15.58 | FX noise |
| 2026-02 | `storageFee.storageFee` | 370.61 | 373.16 | +2.55 | +0.69% | ±10.65 | FX noise |
| 2026-02 | `refundsObject.Principal` | -141.92 | -141.92 | +0.00 | +0.00% | ±5.00 | FX noise |
| 2026-02 | `refundsObject.Commission` | 11.35 | 11.35 | -0.00 | -0.04% | ±5.00 | FX noise |
| 2026-03 | `chargesObject.Revenue` | 6,332.70 | 6,249.12 | -83.58 | -1.32% | ±179.96 | FX noise |
| 2026-03 | `feesObject.Commission` | -501.64 | -497.50 | +4.14 | +0.82% | ±14.26 | FX noise |
| 2026-03 | `fbaObject.FBAPerUnitFulfillmentFee` | -349.20 | -346.39 | +2.81 | +0.80% | ±9.92 | FX noise |
| 2026-03 | `storageFee.storageFee` | 346.26 | 345.07 | -1.19 | -0.34% | ±9.84 | FX noise |
| 2026-03 | `refundsObject.Principal` | -332.31 | -332.31 | +0.00 | +0.00% | ±9.44 | FX noise |
| 2026-03 | `refundsObject.Commission` | 26.58 | 26.59 | +0.01 | +0.03% | ±5.00 | FX noise |
| 2026-04 | `chargesObject.Revenue` | 6,664.69 | 6,770.19 | +105.50 | +1.58% | ±190.82 | FX noise |
| 2026-04 | `feesObject.Commission` | -534.34 | -548.27 | -13.93 | -2.61% | ±15.30 | FX noise |
| 2026-04 | `fbaObject.FBAPerUnitFulfillmentFee` | -373.54 | -383.32 | -9.78 | -2.62% | ±10.70 | FX noise |
| 2026-04 | `storageFee.storageFee` | 321.82 | 318.61 | -3.21 | -1.00% | ±9.21 | FX noise |
| 2026-04 | `refundsObject.Principal` | -284.99 | -284.90 | +0.09 | +0.03% | ±8.16 | FX noise |
| 2026-04 | `refundsObject.Commission` | 22.80 | 22.80 | +0.00 | +0.00% | ±5.00 | FX noise |
| 2026-05 | `chargesObject.Revenue` | 6,940.67 | 6,816.53 | -124.14 | -1.79% | ±192.08 | FX noise |
| 2026-05 | `feesObject.Commission` | -564.06 | -559.13 | +4.93 | +0.87% | ±15.61 | FX noise |
| 2026-05 | `fbaObject.FBAPerUnitFulfillmentFee` | -413.99 | -410.27 | +3.72 | +0.90% | ±11.46 | FX noise |
| 2026-05 | `storageFee.storageFee` | 312.79 | 313.19 | +0.40 | +0.13% | ±8.66 | FX noise |
| 2026-05 | `refundsObject.Principal` | -940.47 | -960.46 | -19.99 | -2.13% | ±26.03 | FX noise |
| 2026-05 | `refundsObject.Commission` | 76.85 | 76.85 | +0.00 | +0.00% | ±5.00 | FX noise |
| 2026-06 | `chargesObject.Revenue` | 6,645.16 | 6,603.44 | -41.72 | -0.63% | ±190.82 | FX noise |
| 2026-06 | `feesObject.Commission` | -602.79 | -602.75 | +0.04 | +0.01% | ±17.31 | FX noise |
| 2026-06 | `fbaObject.FBAPerUnitFulfillmentFee` | -454.20 | -454.20 | +0.00 | +0.00% | ±13.04 | FX noise |
| 2026-06 | `storageFee.storageFee` | 288.90 | 293.02 | +4.12 | +1.43% | ±8.30 | FX noise |
| 2026-06 | `refundsObject.Principal` | 0.00 | 0.00 | +0.00 | +0.00% | ±5.00 | FX noise |
| 2026-06 | `refundsObject.Commission` | 0.00 | 0.00 | +0.00 | +0.00% | ±5.00 | FX noise |

**3 CONTENT flags** (post-FX residual beyond the FX band):

- 2026-01 feesObject.Commission -30.07
- 2026-01 fbaObject.FBAPerUnitFulfillmentFee -30.27
- 2026-01 storageFee.storageFee -52.75

## net, on Sellerboard's own basis

Rebuilt from our AUD lines using Sellerboard's own formula: deduct **gross**
shipped cog (its `productCosts`), then credit back the returned units
(its `Value of returned items`, which sits inside `refundCostsTotal`).
Only the inventory-loss gap is borrowed from Sellerboard — `listTransactions`
cannot see stock that never sold.

| month | ours (USD) | Sellerboard netProfit | Δ | Δ% |
|---|---:|---:|---:|---:|
| 2026-01 | 1,252.93 | 1,152.00 | -100.93 | -8.76% |
| 2026-02 | 3,360.98 | 3,405.40 | +44.42 | +1.30% |
| 2026-03 | 2,870.48 | 2,764.04 | -106.44 | -3.85% |
| 2026-04 | 2,800.10 | 2,923.14 | +123.04 | +4.21% |
| 2026-05 | 2,655.85 | 2,477.99 | -177.86 | -7.18% |
| 2026-06 | 3,025.45 | 3,010.65 | -14.80 | -0.49% |
| **Σ** | | | **-232.57** | |

## cog (compared USD-to-USD; no FX on either side)

AU sheet is USD, Sellerboard is USD. Converting both by the same rate is a
no-op on the ratio, so cog is compared natively and the FX band does not apply.

`salesCosts` is `units_sold x unit_cog` with inventory losses stripped, so the
like-for-like comparison is our **gross shipped** cog — not the refund-netted
figure. `productCosts` = `salesCosts` + those losses, which `listTransactions`
cannot see.

| month | ours gross cog | salesCosts | Δ | ours returned cog | valueOfReturned | Δ | inventory-loss gap |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-01 | 2,929.74 | 3,016.45 | -86.71 | 541.92 | 403.86 | +138.06 | -144.45 |
| 2026-02 | 3,044.13 | 3,044.13 | +0.00 | 30.99 | 30.99 | +0.00 | -243.20 |
| 2026-03 | 2,050.65 | 2,050.65 | +0.00 | 100.02 | 100.02 | +0.00 | -117.70 |
| 2026-04 | 2,215.33 | 2,215.33 | +0.00 | 61.98 | 131.01 | -69.03 | -69.03 |
| 2026-05 | 2,174.11 | 2,174.11 | +0.00 | 223.98 | 192.99 | +30.99 | -30.99 |
| 2026-06 | 1,873.28 | 1,873.28 | +0.00 | 0.00 | 30.99 | -30.99 | -100.02 |
| **Σ** | | | **-86.71** | | | **+69.03** | **-705.39** |

Our AU workbook unit costs **equal Sellerboard's**: five of six months agree to
the cent. 2026-01's entire -86.71 is one MBUKB1 unit (workbook cog 86.71) whose
order carries no financial transaction — see the S03 orders below.

## cog FX guard

- `GMAKER-3` = 30.9900 USD -> **44.43 AUD** at rate 0.6975 (expected 40..50) ✓
- inverted-conversion failure would give ~21.62 AUD
- double-conversion failure would give ~63.70 AUD
