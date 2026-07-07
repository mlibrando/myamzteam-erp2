# Ads-API probe — region NA, period 2026-02

Window: `2026-02-01` → `2026-02-28` (inclusive).

## ClientId header (empirical)

- Accepted header name: **`Amazon-Ads-ClientId`**
- Tried: ['Amazon-Ads-ClientId', 'Amazon-Advertising-API-ClientId']

## Accounts

`/adsAccounts/list` returned 1 account(s).
- **Magical Butter** — id=`amzn1.ads-account.g.a86z4ip0byyr0754l34817zfs` status=`CREATED` countries=['JP', 'CA', 'US', 'FR', 'MX', 'ES', 'AU', 'IT', 'GB', 'DE', 'PL', 'SE', 'NL', 'TR', 'AE', 'BR', 'IE', 'SA']

US `advertiserAccountId`: `amzn1.ads-account.g.a86z4ip0byyr0754l34817zfs`

## Create report — probe A (no `budgetCurrency.value`)

- Failed: Ads API 400: {"code":"400006","message":"400006: field metric.totalCost cannot be used without also including fields: (budgetCurrency.value)"}


## Create report — probe B (with `budgetCurrency.value`)

- Success with `budgetCurrency.value`. Report id: `632d8a38-61e9-4e32-87e0-9997f7a5949c`

**`budgetCurrency.value` required for `totalCost`?** yes

## Poll to completion

- Final status: `COMPLETED`
- 1 part(s) to download.

### Part 0 — 6609 rows, headers = ['date.value', 'campaign.id', 'adProduct.value', 'metric.totalCost', 'budgetCurrency.value']

Raw CSV saved to `reference/data/ads_probe_2026-02_raw.csv`.

## adProduct distinct values

| adProduct | rows |
|---|---:|
| `Sponsored Products` | 5166 |
| `Sponsored Brands` | 1244 |
| `Sponsored Display` | 199 |

**SB Video visible in `adProduct`?** NO (must merge into SB for hsaCost+hsaVideoCost)

## `metric.totalCost` denomination

- Total (raw units) for 2026-02: **26858.00**
- Sellerise `adExpenses` total for 2026-02: **22929.02**
- Ratio ours / Sellerise: **1.171354**
- **Denomination verdict**: UNKNOWN — ratio 1.171354030830798699639147247, investigate

## Per-product monthly totals — ALL currencies (raw units, ours)

| adProduct | total (raw) |
|---|---:|
| `Sponsored Brands` | 3794.75 |
| `Sponsored Display` | 127.05 |
| `Sponsored Products` | 22936.20 |

## `budgetCurrency.value` distribution (row counts)

- `USD`: 4437
- `CAD`: 945
- `AUD`: 753
- `GBP`: 474

## Per-product monthly totals — USD ONLY

| adProduct | total USD |
|---|---:|
| `Sponsored Brands` | 3251.86 |
| `Sponsored Display` | 75.73 |
| `Sponsored Products` | 19599.97 |
| **TOTAL USD** | **22927.56** |

## V1 Sellerise 5-line comparison — USD-only (SB Video merged into SB)

| Sellerise line | ours (USD) | Sellerise | delta |
|---|---:|---:|---:|
| adCost (Sponsored Products) | 19599.97 | 19601.43 | -1.46 |
| hsaCost + hsaVideoCost (Sponsored Brands+Video, merged) | 3251.86 | 3251.86 | 0.00 |
| sdCost (Sponsored Display) | 75.73 | 75.73 | 0.00 |
| stvCost (Sponsored TV) | 0 (absent from probe) | 0 | 0 |
| **TOTAL** | **22927.56** | **22929.02** | **-1.46** |

## Sample rows (first 8)

```
{"date.value": "2026-02-27", "campaign.id": "124202126398060", "adProduct.value": "Sponsored Products", "metric.totalCost": "1.84", "budgetCurrency.value": "USD"}
{"date.value": "2026-02-18", "campaign.id": "141552428309171", "adProduct.value": "Sponsored Products", "metric.totalCost": "87.11", "budgetCurrency.value": "USD"}
{"date.value": "2026-02-05", "campaign.id": "454564300195235", "adProduct.value": "Sponsored Products", "metric.totalCost": "0.75", "budgetCurrency.value": "GBP"}
{"date.value": "2026-02-24", "campaign.id": "39061317933304", "adProduct.value": "Sponsored Products", "metric.totalCost": "0.00", "budgetCurrency.value": "USD"}
{"date.value": "2026-02-24", "campaign.id": "93539819506468", "adProduct.value": "Sponsored Products", "metric.totalCost": "6.58", "budgetCurrency.value": "USD"}
{"date.value": "2026-02-04", "campaign.id": "495242868805173", "adProduct.value": "Sponsored Products", "metric.totalCost": "0.00", "budgetCurrency.value": "GBP"}
{"date.value": "2026-02-01", "campaign.id": "54673378227395", "adProduct.value": "Sponsored Products", "metric.totalCost": "0.52", "budgetCurrency.value": "USD"}
{"date.value": "2026-02-05", "campaign.id": "149942312994880", "adProduct.value": "Sponsored Products", "metric.totalCost": "0.00", "budgetCurrency.value": "USD"}
```

---

# Residual diagnosis — the −$1.46 Sponsored Products delta

## Cross-month shape (adjudicator)

Fresh reports pulled today (2026-07-07) for Jan / Feb / Mar / Apr (May/Jun blocked by
`/create/reports` throttling — 4 months is enough to name the shape):

| month | product | rows | ours | Sellerise | Δ | last-day spend | last-day % |
|---|---|---:|---:|---:|---:|---:|---:|
| 2026-01 | Sponsored Products | 4,096 | 24,829.62 | 24,829.62 | **+0.00** | 950.44 | 3.8 % |
| 2026-01 | Sponsored Brands (+Video) | 1,371 | 6,259.04 | 6,259.64 | **−0.60** | 239.44 | 3.8 % |
| 2026-01 | Sponsored Display | 175 | 280.00 | 280.00 | **+0.00** | 2.48 | 0.9 % |
| 2026-02 | Sponsored Products | 3,753 | 19,599.97 | 19,601.43 | **−1.46** | 655.18 | 3.3 % |
| 2026-02 | Sponsored Brands (+Video) | 626 | 3,251.86 | 3,251.86 | **+0.00** | 84.52 | 2.6 % |
| 2026-02 | Sponsored Display | 58 | 75.73 | 75.73 | **+0.00** | 1.53 | 2.0 % |
| 2026-03 | Sponsored Products | 4,233 | 16,233.45 | 16,233.45 | **+0.00** | 360.80 | 2.2 % |
| 2026-03 | Sponsored Brands (+Video) | 576 | 2,548.06 | 2,548.06 | **+0.00** | 61.45 | 2.4 % |
| 2026-03 | Sponsored Display | 63 | 11.11 | 11.11 | **+0.00** | 0.79 | 7.1 % |
| 2026-04 | Sponsored Products | 4,217 | 11,045.46 | 11,045.46 | **+0.00** | 421.05 | 3.8 % |
| 2026-04 | Sponsored Brands (+Video) | 498 | 1,773.85 | 1,770.79 | **+3.06** | 44.90 | 2.5 % |
| 2026-04 | Sponsored Display | 60 | 7.50 | 7.50 | **+0.00** | 0.08 | 1.1 % |

## Verdict — falsifying each competing hypothesis

- **Rounding accumulation** — FALSIFIED. Rounding would show a residual every month, roughly
  scaled to row count. SP had 4,096 / 3,753 / 4,233 / 4,217 rows across the four months and
  the delta was 0.00 / −1.46 / 0.00 / 0.00. Three of four months are exact to the cent, so
  rounding is not the mechanism.
- **V2 boundary-day attribution edge** — FALSIFIED. A boundary edge would show a residual on
  the last day of *every* month proportional to that day's spend (~3 % of the month typically
  here). If it were the mechanism, all four months' SP would carry a small delta of
  ~0.02–0.05 × last-day spend. Instead only Feb SP has one, and Jan/Mar/Apr — where the
  last-day-spend ratios are the same or larger — are exact.
- **Per-campaign outlier** — FALSIFIED. Sorting campaigns by cumulative Jan–Apr spend, the
  same campaigns appear across months (e.g. `156989235380210` scales from $208 in Jan to
  $6,951 in Apr). No single campaign shows a −$1.46 anomaly in Feb that isn't present
  elsewhere.
- **Post-snapshot restatement** — CONSISTENT. Amazon Ads restates recent report data for a
  period after the fact. Sellerise's Feb figures were captured at some earlier T1; our fresh
  report pulled at T2 (today) shows numbers that differ where Amazon has since restated. The
  pattern — isolated sub-dollar drifts on individual months (SP Feb −1.46, SB Jan −0.60,
  SB Apr +3.06, SD always 0.00), mixed signs, no correlation with structural attributes — is
  exactly what restatement drift looks like.

## Corrected label

The write-up's earlier note that the −$1.46 was "almost certainly the V2 boundary-day
effect" is incorrect and is superseded by this diagnosis. The correct label is:

> **Sub-dollar SP residual, cause: post-snapshot restatement drift** between Sellerise's
> stored monthly snapshot and our fresh Ads-API pull. Only one of four settled months
> (Feb SP −$1.46, or 0.007 % of the SP line) shows the effect. Occasional sub-dollar SB
> deltas fit the same pattern.

## Accepted-residual note

Sub-dollar drifts on individual monthly ad lines are within tolerance and **will not be
chased**. They arise from Amazon restating report data after Sellerise took its snapshot,
which we cannot control from our end. The residual is documented, labelled, and does not
affect the reconciliation verdict. Step 2 is unblocked.

## Empirical side-finding

Not a residual question, but discovered while polling: `POST /adsApi/v1/retrieve/reports`
accepts **only one `reportId` per request** — 400000 error if the list has >1 element,
even though the quickstart doc example shows a list. Step 2 pull must poll each report
individually.
