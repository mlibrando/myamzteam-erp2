# Reference docs — MYAMZTEAM P&L ERP

Drop this `reference/` folder into the repo root. The Claude Code prompt refers to these
files as the authoritative API reference for the build, because the live Amazon Ads doc site
(`advertising.amazon.com/API/docs/*`) is JavaScript-rendered and can't be fetched by a
non-browser tool. Everything here is copied from official Amazon documentation.

## Contents

### `ads-v1/` — Amazon Ads API (the ad-spend source)
- `reporting-overview.md` — metrics categories; `metric.totalCost` (spend) is a Traffic metric.
- `reporting-quickstart.md` — create → retrieve (poll) → download flow.
- `reporting-helpful-concepts.md` — dimensions vs metrics, fields, compatibility, accounts.
- `reporting-new-features.md` — partitioned files, currency conversion (not used — native only).
- `dimension-date.md` — `date.value` (daily grain).
- `dimension-ad-product.md` — `adProduct.value` (SP/SB/SD/STV split).
- `dimension-campaign.md` — `campaign.*` fields incl. `campaign.country` (marketplace filter).
- `dimension-budget-currency.md` — `budgetCurrency.value` (native currency tag).
- `retrieving-accounts.md` — `POST /adsAccounts/list`, `GET /adsAccounts/{id}` → `adsAccountId`.
- `profiles.md` — `GET /v2/profiles` → `profileId` / `countryCode` / `currencyCode` / `marketplaceStringId`.
- `endpoints-regional-hosts.md` — NA/EU/FE ads hosts + header params + Query Publishers example.
- `create-reports-samples.md` — `create/reports` request/response + the locked spend query; QueryCampaign reference.

### `sp-api/` — Amazon SP-API (the P&L backbone)
- `sp-api-endpoints.md` — NA/EU/FE endpoints + AWS regions, marketplace IDs, token→host map, key ops.
  (Full Finances/Sales references are fetchable at `developer-docs.amazon.com/sp-api` — not JS-gated.)

### `data/` — reconciliation targets
- `RAW_AMZ_US_SELLERISE.xlsx` — the US monthly P&L to reproduce to the cent.
- `COGS_Magical_Butter_1.xlsx` — per-SKU COGS (sheets US/CA/AU/UK), native currency.

## Auth-header caveat (unresolved by docs — probe it)
Amazon's own pages disagree on the Ads ClientId header: the reporting reference shows
`Amazon-Ads-ClientId`; profiles/query endpoints use `Amazon-Advertising-API-ClientId`
(+ `Amazon-Advertising-API-Scope` for query calls). Phase 0 resolves this with a two-request
probe rather than assuming.
