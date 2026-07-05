# Amazon SP-API — Endpoints & Marketplace IDs

> Source: official `developer-docs.amazon.com/sp-api` (SP-API Endpoints; Marketplace IDs). Endpoints table provided by the developer; marketplace IDs retrieved from the official page.

## SP-API endpoints

Direct each request to the correct endpoint based on the target marketplace.

| Selling region | Endpoint | AWS region |
| --- | --- | --- |
| North America (Canada, US, Mexico, Brazil) | `https://sellingpartnerapi-na.amazon.com` | `us-east-1` |
| Europe (Ireland, Spain, UK, France, Belgium, Netherlands, Germany, Italy, Sweden, South Africa, Poland, Saudi Arabia, Egypt, Turkey, UAE, India) | `https://sellingpartnerapi-eu.amazon.com` | `eu-west-1` |
| Far East (Singapore, Australia, Japan) | `https://sellingpartnerapi-fe.amazon.com` | `us-west-2` |

## Marketplace IDs (this project's four)

| Marketplace | Marketplace ID | Region → Endpoint | Currency |
| --- | --- | --- | --- |
| US | `ATVPDKIKX0DER` | NA → `sellingpartnerapi-na.amazon.com` | USD |
| CA | `A2EUQ1WTGCTBG2` | NA → `sellingpartnerapi-na.amazon.com` | CAD |
| UK | `A1F83G8C2ARO7P` | EU → `sellingpartnerapi-eu.amazon.com` | GBP |
| AU | `A39IBJ37TRP1C6` | FE → `sellingpartnerapi-fe.amazon.com` | AUD |

## Refresh-token → endpoint mapping (env)

| Env var | Covers | SP-API host |
| --- | --- | --- |
| `AMAZON_SP_REFRESH_TOKEN_NA` | US, CA | `sellingpartnerapi-na.amazon.com` |
| `AMAZON_SP_REFRESH_TOKEN_EU` | UK | `sellingpartnerapi-eu.amazon.com` |
| `AMAZON_SP_REFRESH_TOKEN_FE` | AU | `sellingpartnerapi-fe.amazon.com` |

## Key operations used by this build

- **Finances `listTransactions` (v2024-06-19):** `GET /finances/2024-06-19/transactions` — rate 0.5 req/s (burst 10); excludes the last ~48h; `postedAfter`/`postedBefore` ≤ 180 days apart per call. Full reference: `developer-docs.amazon.com/sp-api/docs/finances-api-v2024-06-19-reference`.
- **Sales `getOrderMetrics` (v1):** `GET /sales/v1/orderMetrics` — top-line sales/units, up to ~2 years, granularity Day. Reference: `developer-docs.amazon.com/sp-api/docs/sales-api-v1-reference`.
