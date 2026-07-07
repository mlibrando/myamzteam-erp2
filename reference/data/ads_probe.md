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
