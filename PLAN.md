# MYAMZTEAM P&L ERP — Implementation Plan

## Context

MYAMZTEAM currently maintains its Amazon Profit & Loss report by hand in Sellerise. The
US worksheet in `reference/data/RAW_AMZ_US_SELLERISE.xlsx` (sheet `RAW_AMZ_US`) is the
ground truth: a monthly time series with buckets Sales / Cost of Goods / Taxes / FBA
fees / Referral fees / Storage fees / Advertising / Refunds / Other AMZ transactions,
plus Net Profit / Margin / ROI. This project builds an automated internal ERP that
reproduces that table per marketplace from official Amazon APIs and a manual COGS file,
shipping the US pipeline first and widening to CA / UK / AU afterward.

A single seller account operates all four stores. History depth starts at **Jan 2026**
to match the sheet. Each marketplace stays in its native currency — no FX conversion.
The dashboard reads only from Postgres; Amazon is called by a scheduled sync, never in
the request path.

## Architecture at a glance

```
Railway cron ─► Python sync module
                 ├─ SP-API Finances listTransactions  ─┐
                 ├─ SP-API Sales   getOrderMetrics     ├─► Postgres (Railway)
                 ├─ Ads-v1 create/retrieve/download    │
                 └─ COGS workbook parse                ┘
                                                        │
                          FastAPI ◄──────────────────── │
                            │
                          Next.js dashboard
```

- **Backend:** FastAPI. **Frontend:** Next.js. **DB:** Postgres.
- **HTTP:** `httpx` — no AWS SDK (SP-API is bearer-only; SigV4 is not required).
- **Excel:** `openpyxl` with `data_only=True` so formula cells return cached values.
- **Sync:** one Python module, invoked by Railway cron. No Celery / queue.

## Data model (Postgres)

Tables (single-tenant; no `account_id` partition):

- `sp_transactions` — `transaction_id` (PK, from API), `marketplace_id`, `posted_at`,
  `total_amount`, `currency`, `raw_json`.
- `sp_breakdowns` — `id`, `transaction_id` (FK), `breakdown_type` (free-form string),
  `breakdown_amount`, `currency`.
- `sp_transaction_items` — `id`, `transaction_id` (FK), `sku`, `asin`,
  `quantity_shipped`.
- `sales_daily` — `marketplace_id`, `date`, `unit_count`, `order_item_count`,
  `total_sales`, `average_unit_price`. PK `(marketplace_id, date)`.
- `ads_reports` — `id`, `marketplace_id`, `period_start`, `period_end`, `amazon_report_id`,
  `status`, `created_at`, `completed_at`, `failure_code`, `failure_reason`.
- `ad_spend_daily` — `id`, `marketplace_id`, `date`, `ad_product`, `campaign_id`,
  `campaign_name`, `campaign_country`, `budget_currency`, `total_cost`.
  Upsert on `(marketplace_id, date, campaign_id, ad_product)`.
- `cogs_per_sku` — `marketplace_id`, `sku`, `asin`, `product_name`, `status`,
  `normal_price`, `cogs` (per-unit, native currency), `imported_at`. PK
  `(marketplace_id, sku)`.
- `sync_state` — `key` (e.g. `sp_finances:US`, `ads:US`, `sales:US`), `last_posted_at`,
  `next_token`, `updated_at`. Enables resumable cursored syncs.
- `unmapped_breakdown_types` — `breakdown_type`, `first_seen`, `last_seen`, `occurrences`,
  `sample_transaction_id`. Surfaces gaps in the bucket map.
- `pnl_monthly` — `marketplace_id`, `year_month` (`YYYY-MM`), `line_key`,
  `line_label`, `bucket`, `amount`, `currency`, `computed_at`. Populated at end of sync.

Money is stored as `numeric(18,4)` to avoid float drift.

## Environment (reference by name only — never print values)

```
DATABASE_URL
AMAZON_SP_CLIENT_ID
AMAZON_SP_CLIENT_SECRET
AMAZON_SP_REFRESH_TOKEN_NA   # US + CA
AMAZON_SP_REFRESH_TOKEN_EU   # UK
AMAZON_SP_REFRESH_TOKEN_FE   # AU
AMAZON_ADS_CLIENT_ID
AMAZON_ADS_CLIENT_SECRET
AMAZON_ADS_REFRESH_TOKEN_NA  # single ads token — assumed to cover NA/EU/FE; Phase 0 verifies
```

---

## Phase 0 — Scaffold & verify ✅ DONE (partial)

**Goal:** repo layout, env wiring, DB schema, and a written re-verification of every
API fact including the two ambiguous ads-v1 header contradictions.

**Steps:**

1. Repo skeleton (as built):
   ```
   backend/
     app/                   # FastAPI (stub — populated in Phase 5)
     sync/
       __init__.py
       __main__.py          # CLI: python -m sync [--marketplace US] [--start ISO]
       config.py            # RegionConfig dataclass, MARKETPLACE_TO_REGION, MARKETPLACE_CURRENCY
       sp_client.py         # LWA + httpx wrapper, 0.5 rps token-bucket limiter
       finances.py          # listTransactions cursor sync
       ads_client.py        # (Phase 4)
       sales.py             # (Phase 5)
       ads.py               # (Phase 4)
       cogs.py              # (Phase 3)
       aggregate.py         # (Phase 2)
       reconcile.py         # (Phase 2)
     db/
       __init__.py
       migrations/          # Alembic migrations (hand-written, no autogenerate)
         env.py             # loads DATABASE_URL from .env; rewrites postgres:// prefix
         versions/
           feccfae1778b_initial_schema.py  # all 11 tables
   pyproject.toml           # direct-deps source-of-truth (not used for editable install)
   requirements.txt         # pip freeze — exact pins, 30 packages; used for deployment
   alembic.ini
   ```
   > **Note:** `db/schema.sql` and `db/migrate.py` were replaced by Alembic before
   > any schema was applied. Apply migrations with `alembic upgrade head`. To adopt a
   > DB that already has the tables, use `alembic stamp head` instead.
2. Postgres schema applied via Alembic revision `feccfae1778b` — all 11 tables.
   DB on Railway was stamped (tables already existed from a prior run).
3. Railway service wiring: backend web service, cron trigger running `python -m sync`
   once daily at 04:00 UTC (after the 48h SP-API lag). *(cron not yet configured)*
4. **Documentation re-verification pass.** Re-fetch every source below and record a
   ✅ / ❌ status in this file's "Documentation references" section:
   - `https://developer-docs.amazon.com/sp-api/docs/finances-api-v2024-06-19-reference`
   - `https://developer-docs.amazon.com/sp-api/docs/sales-api-v1-reference`
   - `https://developer-docs.amazon.com/sp-api/docs/marketplace-ids`
   - `https://developer-docs.amazon.com/sp-api/docs/sp-api-endpoints`
   - `https://developer-docs.amazon.com/sp-api/docs/connecting-to-the-selling-partner-api`
   - `https://developer-docs.amazon.com/llms.txt`
   - `reference/ads-v1/*.md`, `reference/sp-api/sp-api-endpoints.md`
5. **Ads auth-header two-request probe.** *(pending — Phase 4 prerequisite)*
6. **Ads token region probe.** *(pending — Phase 4 prerequisite)*

**DB tables touched:** none (schema is created; no rows written).

**Acceptance check:** `backend/` and `frontend/` boot; DB schema applied;
`PLAN.md` is amended with a filled-in verification section including the probe outcome
(header names, region reachability).

---

## Phase 1 — SP-API client + Finances sync (US) ✅ DONE (smoke test passed; full backfill pending)

**Goal:** land every US transaction posted from Jan 2026 onward, plus its breakdowns
and items, into Postgres, with a resumable cursor.

**Depends on:**
- `GET /finances/2024-06-19/transactions` — 0.5 rps, burst 10, 48h lag, ≤180d window,
  `nextToken` pagination. Source:
  [`finances-api-v2024-06-19-reference`](https://developer-docs.amazon.com/sp-api/docs/finances-api-v2024-06-19-reference).
- NA host `https://sellingpartnerapi-na.amazon.com`. Auth: `x-amz-access-token` (LWA);
  no SigV4. Source:
  [`connecting-to-the-selling-partner-api`](https://developer-docs.amazon.com/sp-api/docs/connecting-to-the-selling-partner-api).

**Steps:**

1. `sp_client.py`:
   - LWA refresh via `https://api.amazon.com/auth/o2/token` (`grant_type=refresh_token`).
     Cache access token in memory until 60s before expiry.
   - **Sync (not async)** — `httpx.Client` with a token-bucket enforcing 0.5 rps +
     burst 10 via `time.sleep()`. Async was not needed for a single-threaded cron sync.
   - Retry 429 / 5xx with exponential backoff (starts 1s, caps 60s, max 6 attempts).
     Force-refresh LWA token on 401.
2. `finances.py`:
   - Backfill window: iterate **179-day** slices (`WINDOW_DAYS = 179` — safely under
     the 180-day API limit) from `2026-01-01` forward, honoring the 48-hour lag on the
     trailing edge.
   - For each `listTransactions` page: upsert `sp_transactions`, then delete + re-insert
     `sp_breakdowns` and `sp_transaction_items` (idempotent — avoids stale child rows).
   - Breakdowns are a **recursive tree** in the API response. Only **leaf nodes**
     (nodes with no children) are inserted into `sp_breakdowns` to avoid double-counting.
     Both transaction-level and item-level breakdowns are flattened.
   - When `nextToken` is present, pass **only** `nextToken` — no other query params.
     This is Amazon's convention for cursor-based pagination.
   - Persist `next_token` + `last_posted_at` to `sync_state` (key: `sp_finances:{marketplace_id}`)
     between pages for crash-resume.
3. Incremental mode: on subsequent runs, start from `sync_state.last_posted_at` minus
   24h overlap up to `now() - 48h`.

**Confirmed API response shape (live):**
```
{
  "payload": {
    "transactions": [
      {
        "transactionId": "...",
        "postedDate": "2026-07-01T...",
        "totalAmount": {"currencyCode": "USD", "currencyAmount": 12.34},
        "marketplaceDetails": {"marketplaceId": "ATVPDKIKX0DER"},
        "breakdowns": [...],   // recursive tree — flatten leaves only
        "items": [
          {"contexts": [{"sku": "...", "asin": "...", "quantityShipped": 1, ...}]}
        ]
      }
    ],
    "nextToken": "..."   // omitted on last page
  },
  "statusCode": 200
}
```
`marketplaceId` is a valid server-side filter query param — only matching transactions
are returned, which keeps window sizes manageable.

**Smoke test results (Jul 1–3, 2026 · US):**
- 287 transactions / 2 185 breakdowns / 296 items ingested in ~2 min.
- Second run: 0 new rows inserted — idempotency confirmed.
- No 429s observed.

**Observed `breakdownType` values (preview for Phase 2 mapping):**
`Base`, `OurPricePrincipal`, `ProductCharges`, `OurPriceTax`,
`MarketplaceFacilitatorTax-Principal`, `ShippingPrincipal`, `Shipping`,
`PromoRebates`, `ShippingDiscount`, `RecommerceLiquidation`, `AmazonFees`,
`Sales`, `Expenses`, `LiquidationReferralFee`, `LiquidationProcessingFee`.
All unmapped types are surfaced via `unmapped_breakdown_types` table.

**Full Jan 2026 backfill:** deferred — will run `python -m sync --marketplace US
--start 2026-01-01T00:00:00Z` as a separate session.

**DB tables touched:** `sp_transactions`, `sp_breakdowns`, `sp_transaction_items`,
`sync_state`.

**Acceptance check:** After a full US backfill, `SELECT COUNT(*) FROM sp_transactions
WHERE marketplace_id = 'ATVPDKIKX0DER'` is non-empty; re-running the sync inserts zero
new rows (idempotency). No sustained 429s in logs.

---

## Phase 2 — P&L mapping + reconciliation (US)

**Goal:** produce a US monthly P&L that ties to `RAW_AMZ_US_SELLERISE.xlsx` **to the cent**.

**Steps:**

1. `backend/bucket_map.py` — the reconciliation heart. Python constant:
   ```python
   BUCKET_MAP: dict[str, str] = {
       # "Sales" bucket
       "Principal": "sales.product_sales",
       # "Tax": "sales.tax",
       # ...authored against the sheet's sub-line labels...
   }
   ```
   Values use dotted paths `{bucket}.{sub_line}` mirroring rows 2–71 of the sheet.
   Author entries by fetching a representative month's raw breakdowns and mapping each
   observed `breakdownType` to a sheet row, then confirming the sums tie.
2. `aggregate.py` — for each `(marketplace_id, year_month)`:
   - Sum `sp_breakdowns.breakdown_amount` grouped by mapped `bucket.sub_line`.
   - Any `breakdown_type` not in `BUCKET_MAP` → upsert `unmapped_breakdown_types` with
     an occurrence count and sample transaction; also write a total to a
     `sales.unmapped` line so nothing is silently dropped.
   - Compute Net Profit = Σ(all buckets); Margin = Net Profit / Sales; ROI is left
     null until Phase 3 (needs COGS).
   - Truncate & write `pnl_monthly` for US.
3. `reconcile.py` — read `RAW_AMZ_US_SELLERISE.xlsx` via `openpyxl(data_only=True)`,
   compare cell-by-cell to `pnl_monthly` filtered to US. Emit a diff CSV listing
   `(row_label, year_month, sheet_value, computed_value, delta)` for every cell where
   `|delta| ≥ $0.01`.

**DB tables touched:** `pnl_monthly`, `unmapped_breakdown_types`.

**Acceptance check:** `reconcile.py` reports zero rows for the US sheet (all deltas
< $0.01). `unmapped_breakdown_types` is either empty or every entry has been reviewed
and consciously left uncategorized.

---

## Phase 3 — COGS (US)

**Goal:** derive monthly Cost of Goods from units sold × per-unit COGS; update `Cost
of Goods`, `Net Profit`, and `ROI` rows.

**Depends on:** [`reference/data/COGS_Magical_Butter_1.xlsx`](reference/data/COGS_Magical_Butter_1.xlsx) — sheets `US` `CA` `AU` `UK`.

**Steps:**

1. `cogs.py`:
   - Read the workbook with `openpyxl(data_only=True)` so formula cells like `=2.12*4`
     return the cached numeric result.
   - Read by header name, not column index — the AU sheet is missing `Status`.
   - **Hard-fail on duplicate SKU within a sheet.** Two US rows share a SKU; the
     import must raise with the offending SKU listed before writing any row.
   - Upsert `cogs_per_sku`.
2. Units sold per SKU per month: aggregate `sp_transaction_items.quantity_shipped`
   grouped by `sku` and `posted_at` month, joined via `transaction_id` to the
   marketplace.
3. Monthly COGS per marketplace = Σ(units_sold_by_sku × cogs_per_sku.cogs). Join on
   `sku`, fallback to `asin`. Any SKU with sales but no COGS row is surfaced (mirrors
   the `unmapped_breakdown_types` pattern via a `cogs_missing_skus` table).
4. Recompute `Net Profit` and `ROI` = Net Profit / |Cost of Goods| in `pnl_monthly`.

**DB tables touched:** `cogs_per_sku`, `pnl_monthly` (Cost of Goods, Net Profit, ROI
rows).

**Acceptance check:** `reconcile.py` shows zero deltas ≥ $0.01 on the Cost of Goods,
Net Profit, Margin, and ROI rows for the US sheet. `cogs_missing_skus` is empty (or
consciously reviewed).

---

## Phase 4 — Advertising spend (US)

**Goal:** land daily US ad spend from Ads-v1 reports; aggregate into the Advertising
bucket's 5 sub-lines matching the Sellerise sheet.

**Depends on:**
- [`reference/ads-v1/reporting-quickstart.md`](reference/ads-v1/reporting-quickstart.md), [`reference/ads-v1/create-reports-samples.md`](reference/ads-v1/create-reports-samples.md),
  [`reference/ads-v1/retrieving-accounts.md`](reference/ads-v1/retrieving-accounts.md), [`reference/ads-v1/endpoints-regional-hosts.md`](reference/ads-v1/endpoints-regional-hosts.md).
- NA host `https://advertising-api.amazon.com`.
- Accepted ClientId header + probe outcomes from Phase 0.

**Steps:**

1. `ads_client.py`:
   - LWA refresh (separate app from SP-API), token URL
     `https://api.amazon.com/auth/o2/token`, scope
     `advertising::campaign_management`. Cache access token for < 60 min.
2. Account discovery: `POST /adsAccounts/list` → pick the single account whose
   `countryCodes` includes `US` → capture its `adsAccountId` and the US entry from
   `alternateIds` (`profileId`, `entityId`). Store on a config row (or an in-memory
   const in `ads.py` if it never changes).
3. Report creation per US month gap:
   - `POST /adsApi/v1/create/reports` body:
     ```json
     {
       "accessRequestedAccounts": [{"advertiserAccountId": "<adsAccountId>"}],
       "reports": [{
         "format": "GZIP_JSON",
         "periods": [{"datePeriod": {"startDate": "2026-01-01", "endDate": "2026-01-31"}}],
         "query": {
           "fields": [
             "date.value", "adProduct.value",
             "campaign.id", "campaign.name", "campaign.country",
             "budgetCurrency.value", "metric.totalCost"
           ],
           "filter": { "campaign.country": ["US"] }
         }
       }]
     }
     ```
   - 207 response: on `success[]` entry, insert `ads_reports` row with `PENDING`.
4. Polling: `POST /adsApi/v1/retrieve/reports` once per minute against outstanding
   report IDs until `COMPLETED` or `FAILED`. On `FAILED`, persist `failureCode` /
   `failureReason` and stop.
5. Download: for each `completedReportParts[].url` (S3 pre-signed, watch
   `urlExpirationDateTime`), stream, decompress if gzip, iterate records. Upsert
   `ad_spend_daily` on `(marketplace_id, date, campaign_id, ad_product)`.
6. Aggregate `total_cost` by month + `ad_product`:
   - `SPONSORED_PRODUCTS` → `advertising.sponsored_products`
   - `SPONSORED_BRANDS` → `advertising.sponsored_brands_including_video`
     (reconcile against sheet rows `Sponsored brands` + `Sponsored videos` summed)
   - `SPONSORED_DISPLAY` → `advertising.sponsored_display`
   - `SPONSORED_TELEVISION` → `advertising.sponsored_television`
7. Write results to `pnl_monthly` and recompute Net Profit / Margin / ROI.

**DB tables touched:** `ads_reports`, `ad_spend_daily`, `pnl_monthly` (Advertising +
KPI rows).

**Acceptance check:** `reconcile.py` shows the Advertising bucket total matching the
sheet's `Sponsored brands + Sponsored display + Sponsored videos + Sponsored
television + Sponsored products` sum, and the combined `Sponsored brands + Sponsored
videos` sub-sum matches API `SPONSORED_BRANDS`.

---

## Phase 5 — Dashboard (US)

**Goal:** Next.js page that reproduces the Sellerise table plus a sales trend line.

**Depends on:**
- FastAPI endpoint `GET /pnl?marketplace=US&start=2026-01&end=2026-12` reading
  `pnl_monthly` only.
- Sales trend from `sales_daily` (populated by a small `sales.py` module calling
  `getOrderMetrics` with `granularity=Day` and the US marketplace ID).

**Steps:**

1. `sales.py`: incremental daily fetch of `GET /sales/v1/orderMetrics` into
   `sales_daily`. **Note: live docs do not state a rate limit for this endpoint** —
   apply the SP-API-wide 0.5 rps ceiling defensively.
2. FastAPI routes:
   - `GET /pnl` returns rows shaped exactly like the sheet (row label + month columns).
   - `GET /sales-trend` returns daily totals.
   - `GET /reconcile` (dev-only) triggers `reconcile.py` and returns the diff CSV.
3. Next.js `/app/pnl/page.tsx`:
   - Marketplace selector (US only in Phase 5; other options disabled).
   - Month range control (default: Jan 2026 → current month).
   - P&L table replicating the sheet's row order.
   - Sales-trend line chart underneath.

**DB tables touched:** `sales_daily` (write); `pnl_monthly`, `sales_daily` (read).

**Acceptance check:** Loading `/pnl?marketplace=US` in a browser shows numbers that
match the sheet (spot-check a few cells); the trend chart shows daily units and sales;
no request path touches Amazon.

---

## Phase 6 — Widen to CA, UK, AU

**Goal:** repeat Phases 1–4 for CA (NA / same SP token / CAD), UK (EU / `SP_REFRESH_TOKEN_EU` / GBP),
AU (FE / `SP_REFRESH_TOKEN_FE` / AUD).

**Steps:**

1. Region routing table in `sp_client.py`:
   ```
   ATVPDKIKX0DER (US) → NA / SP_REFRESH_TOKEN_NA
   A2EUQ1WTGCTBG2 (CA) → NA / SP_REFRESH_TOKEN_NA
   A1F83G8C2ARO7P (UK) → EU / SP_REFRESH_TOKEN_EU
   A39IBJ37TRP1C6 (AU) → FE / SP_REFRESH_TOKEN_FE
   ```
2. Add marketplace loops to `finances.py`, `sales.py`, `ads.py`.
3. Ads region routing: use `AMAZON_ADS_REFRESH_TOKEN_NA` against
   `advertising-api.amazon.com` (US, CA), `advertising-api-eu.amazon.com` (UK), and
   `advertising-api-fe.amazon.com` (AU) — contingent on Phase 0 confirming that the
   single ads token authenticates in all three regions. Filter reports by
   `campaign.country` in `{US, CA, GB, AU}` as appropriate.
4. COGS: import the `CA`, `UK`, `AU` sheets — remember AU has no `Status` column, and
   duplicate-SKU behavior is hard-fail per Phase 3.
5. Native-currency handling: `pnl_monthly.currency` carries USD / CAD / GBP / AUD.
   The dashboard's combined view shows currencies side by side, not summed.

**DB tables touched:** all sync tables, per new `marketplace_id`.

**Acceptance check:** `pnl_monthly` has non-empty rows for each of CA / UK / AU;
dashboard renders each in its native currency; a per-marketplace reconciliation script
(if a sheet is available for that marketplace) shows zero deltas ≥ 1¢/1p.

---

## Verification (end-to-end)

- **DB / sync:** `python -m sync` runs to completion; re-running produces zero net
  row changes (idempotency).
- **Reconciliation:** `python -m sync.reconcile --marketplace US` outputs an empty
  diff CSV for the US sheet.
- **Dashboard:** with the Next.js dev server running, `/pnl?marketplace=US` matches
  the sheet on spot-checked months; the trend chart renders.
- **Rate limits:** logs show no sustained 429s from SP-API; ads polling stays at ~1/min.

## Risks / open items

- **Ads ClientId header contradiction** (`Amazon-Ads-ClientId` vs
  `Amazon-Advertising-API-ClientId`) — resolved empirically in Phase 0. Do NOT
  hard-code before the probe.
- **`create/reports` profile-scope requirement** — Phase 0 also confirms whether
  `Amazon-Advertising-API-Scope` is required for reporting (helpful-concepts implies no,
  since accounts are in the body — but the header inconsistency puts this in doubt).
- **`adsAccountId` vs `advertiserAccountId`** — the reporting body field is
  `advertiserAccountId`; the account response uses `adsAccountId`. First real call
  confirms they carry the same value (helpful-concepts asserts they do).
- **Single ads token across three regions** — assumed by the developer, unverified.
  Phase 0 probe. Fallback: request region-specific ads refresh tokens.
- **Reconciliation-to-the-cent risk from free-form `breakdownType`** — the
  `unmapped_breakdown_types` table surfaces every unknown value the sync encounters.
  New values appearing in production are treated as a blocker until mapped.
- **US COGS sheet has 2 duplicate SKUs among 108 rows** — sync hard-fails until the
  sheet is cleaned. This is intentional: silent collapse would corrupt COGS.
- **US COGS sheet has formula cells** (e.g., `=2.12*4`) — safe because we read with
  `openpyxl(data_only=True)`, which returns the cached numeric result. Must not open
  the workbook with `data_only=False` in the sync.
- **Sales `getOrderMetrics` rate limit not stated** on the live reference — apply the
  0.5 rps SP-API-wide ceiling defensively.
- **AU COGS sheet is missing `Status`** — read by header name, not index.
- **48-hour SP-API data lag** — cron runs at 04:00 UTC and always stops sync at
  `now() - 48h`.
- **CONFIRMED, no longer open:** SP-API auth (LWA bearer only, no SigV4); LWA refresh
  URL `https://api.amazon.com/auth/o2/token`; NA/EU/FE SP-API hosts; NA/EU/FE Ads
  hosts; marketplace IDs; `adProduct.value` enum (SP/SB/SD/STV — no SB Video variant);
  listTransactions response envelope `{payload:{transactions,nextToken},statusCode}`;
  `marketplaceId` filter works server-side; breakdowns are recursive trees (flatten leaves only);
  sync is synchronous (`httpx.Client` + `time.sleep` token bucket), not async.

## Documentation references

| Source | Status |
| --- | --- |
| `developer-docs.amazon.com/sp-api/docs/finances-api-v2024-06-19-reference` | ✅ fetched |
| `developer-docs.amazon.com/sp-api/docs/sales-api-v1-reference` | ✅ fetched (rate limit missing from doc) |
| `developer-docs.amazon.com/sp-api/docs/marketplace-ids` | ✅ fetched |
| `developer-docs.amazon.com/sp-api/docs/sp-api-endpoints` | ✅ fetched |
| `developer-docs.amazon.com/sp-api/docs/connecting-to-the-selling-partner-api` | ✅ fetched (confirms LWA bearer-only) |
| `developer-docs.amazon.com/llms.txt` | ✅ fetched |
| `reference/ads-v1/reporting-overview.md` | ✅ read |
| `reference/ads-v1/reporting-quickstart.md` | ✅ read |
| `reference/ads-v1/reporting-helpful-concepts.md` | ✅ read |
| `reference/ads-v1/reporting-new-features.md` | ✅ read |
| `reference/ads-v1/dimension-date.md` | ✅ read |
| `reference/ads-v1/dimension-ad-product.md` | ✅ read |
| `reference/ads-v1/dimension-campaign.md` | ✅ read |
| `reference/ads-v1/dimension-budget-currency.md` | ✅ read |
| `reference/ads-v1/retrieving-accounts.md` | ✅ read |
| `reference/ads-v1/profiles.md` | ✅ read |
| `reference/ads-v1/endpoints-regional-hosts.md` | ✅ read |
| `reference/ads-v1/create-reports-samples.md` | ✅ read |
| `reference/sp-api/sp-api-endpoints.md` | ✅ read |
| `reference/data/RAW_AMZ_US_SELLERISE.xlsx` | ✅ inspected via openpyxl |
| `reference/data/COGS_Magical_Butter_1.xlsx` | ✅ inspected via openpyxl |
| `advertising.amazon.com/API/docs/*` | ❌ not retrievable (JS-gated; use `reference/ads-v1/` instead) |
| `github.com/amzn/ads-advanced-tools-docs` | ✅ noted as code-samples only (Postman collection is the useful artifact) |
| `github.com/amzn/selling-partner-api-models` | ✅ noted as authoritative schemas (not consulted this pass) |

These sources were fetched/read during planning. Phase 0 (ads header + token-region
probes) will append the two remaining probe results (accepted ClientId header per
endpoint; single-token region reachability) before Phase 4 begins.
