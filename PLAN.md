> **STALE — predates the CA/UK/AU rollout.** Authoritative: `reference/data/` findings + the code.
>
> Two of its acceptance checks are still load-bearing and both are currently **unmet**: `pnl_monthly`
> has no AU rows, and the dashboard it specifies reads `pnl_monthly`, whose CA `cog` is stale.
> See [`reference/data/decisions_audit.md`](reference/data/decisions_audit.md), blockers B3 and B4.

# Amazon P&L ERP — Implementation Plan

## Context

The client currently maintains its Amazon Profit & Loss report by hand. The US worksheet 
in `reference/data/raw_amz_us.xlsx` (sheet `RAW_US`) is the ground truth: a monthly 
time series with buckets Sales / Cost of Goods / Taxes / FBA fees / Referral fees / 
Storage fees / Advertising / Refunds / Other AMZ transactions, plus Net Profit / Margin / 
ROI. This project builds an automated internal ERP that reproduces that table per marketplace 
from official Amazon APIs and a manual COGS file, shipping the US pipeline first and widening 
to CA / UK / AU afterward.

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
- Breakdown-type buckets hardcoded in `finances.py` per the reference above.
- Marketplace ID (`ATVPDKIKX0DER` for US, per [marketplace-ids](https://developer-docs.amazon.com/sp-api/docs/marketplace-ids)).
- LWA bearer token — refreshed on-demand via `sp_client.py`.

**Steps:**

1. `sp_client.py` — LWA token refresh wrapper:
   - On startup, call `POST /auth/o2/token` with `grant_type=refresh_token` and
     `AMAZON_SP_REFRESH_TOKEN_NA` to get a short-lived bearer token.
   - Wrap every SP-API call with a token-bucket limiter (0.5 req/sec, burst 10) to stay
     under the SP-API-wide rate ceiling.
   - On `401 Unauthorized`, refresh and retry once.
   - Log request/response for audit.
2. `finances.py`:
   - Call `GET /finances/2024-06-19/transactions?marketplaceId={US_ID}&postedAfter={cursor}`
     (cursor is `sync_state.last_posted_at` for US, or `2026-01-01T00:00:00Z` on first run).
   - Parse `payload.transactions` and upsert each into `sp_transactions`.
   - For each transaction, recursively flatten `breakdowns` (tree structure; leaf nodes only)
     and upsert into `sp_breakdowns`.
   - For each transaction, upsert `transactionItems` into `sp_transaction_items`.
   - If `payload.nextToken` is set, save it to `sync_state.next_token` and resume from it
     on the next run. **Do not re-query the same `postedAfter`.**
   - Backfill will take multiple cron invocations (180d / ~30d of backlog per run); sync is
     designed to resume from `next_token` across restarts.
3. `reconcile.py` helper: for local development, `python -m sync.reconcile --marketplace US`
   loads the sheet, sums `Sales / COGS / Taxes / ... / Other`, computes Net Profit / Margin / ROI,
   and compares against `pnl_monthly` rows. Output a CSV diff (expected: empty).

**DB tables touched:** `sp_transactions`, `sp_breakdowns`, `sp_transaction_items`, `sync_state`.

**Acceptance check:** Phase 1 passes smoke test (tables written, no errors). Full backfill
acceptance deferred to Phase 2 (reconciliation).

---

## Phase 2 — Aggregation + reconciliation (US)

**Goal:** bucket all transactions into the P&L line items and verify against the reference sheet.

**Depends on:**
- Bucket mapping (hardcoded per Phase 1 breakdown types).
- Reference sheet (for spot-check).
- Idempotent aggregation (running Phase 1 twice does not change `pnl_monthly`).

**Steps:**

1. Define bucket map in `config.py`:
   ```python
   BREAKDOWN_BUCKET_MAP = {
       "Marketplaces Fees": ("fees", "referral_fees"),
       "FBA Fees": ("fees", "fba_fees"),
       "StorageFee": ("fees", "storage_fees"),
       # ... etc
   }
   ```
2. `aggregate.py` module:
   - Read all rows from `sp_transactions`, `sp_breakdowns`, `sp_transaction_items`, `sales_daily`.
   - For each transaction's breakdown, map `breakdown_type` → bucket using `BREAKDOWN_BUCKET_MAP`.
   - If any `breakdown_type` is unmapped, log to `unmapped_breakdown_types` and **block the sync**
     (new unmapped types are treated as a critical error).
   - Aggregate by marketplace + year-month + bucket → totals.
   - Write to `pnl_monthly` (upsert on `marketplace_id, year_month, bucket`).
   - Compute KPIs: Net Profit = Sales - COGS - Taxes - All Fees - Refunds - Other;
     Margin = Net Profit / Sales; ROI = Net Profit / COGS.
   - Write KPI rows to `pnl_monthly` with `line_key` = `kpi.net_profit`, etc.
3. `reconcile.py`:
   - Load the reference sheet and parse buckets from it (sums per row).
   - Query `pnl_monthly` for the same period and compute totals per bucket.
   - Diff: `reference_total - pnl_total` for each bucket. If any diff > $0.01 (or native cent),
     dump CSV and exit non-zero.
   - Idempotency check: running Phase 1 twice should produce a zero diff (no double-counts).

**DB tables touched:** `pnl_monthly`, `unmapped_breakdown_types`.

**Acceptance check:** `python -m sync.reconcile --marketplace US` shows zero diffs for every
bucket (spot-check: Sales, COGS, Sponsored Products, Net Profit, ROI match the sheet). Running
the full sync twice produces identical `pnl_monthly` rows (idempotent).

---

## Phase 3 — COGS import

**Goal:** land per-SKU cost-of-goods from the workbook into `cogs_per_sku`.

**Depends on:**
- COGS workbook with columns: SKU | ASIN | Product Name | Status | Normal Price | COGS (per unit).
- Hard-fail on duplicate SKUs (silent collapse would corrupt the P&L).
- AU sheet has no Status column (read by header, not index).

**Steps:**

1. `cogs.py` module:
   - Parse the COGS workbook (one sheet per marketplace: US / CA / UK / AU).
   - For each row, read SKU, ASIN, Product Name, Status, Normal Price, COGS (native currency).
   - **Hard-fail if any SKU appears twice in the sheet** (intentional; silent collapse is data loss).
   - Read formula cells via `openpyxl(data_only=True)` to get cached numeric values (do NOT
     use `data_only=False`).
   - Upsert into `cogs_per_sku` on `(marketplace_id, sku)`. Set `imported_at = now()`.
2. Deploy script: `python -m sync.cogs --marketplace US` to dry-run or actually import
   (flag: `--apply`).

**DB tables touched:** `cogs_per_sku`.

**Acceptance check:** `cogs_per_sku` for US has ~100+ rows (SKU count). Spot-check a few
SKU → COGS values against the workbook. Running import twice produces identical rows (no
double-inserts, upsert is idempotent).

---

## Phase 4 — Ads sync

**Goal:** fetch Amazon Advertising spend by product, date, and campaign, and aggregate into
the P&L Advertising bucket.

**Depends on:**
- Ads-v1 reporting API with per-dimension reporting (https://advertising.amazon.com).
- Proof-of-concept auth: Phase 0 probes confirm the correct ClientId header and that the
  single ads token authenticates in all three regions (NA, EU, FE).
- Ads account ID (maps campaigns to the seller).
- Campaign metadata (name, country, budget currency).

**Steps:**

1. `ads_client.py` — Ads-v1 auth wrapper (similar structure to `sp_client.py`):
   - On startup, call `POST /auth/o2/token` with `grant_type=refresh_token` and
     `AMAZON_ADS_REFRESH_TOKEN_NA` to get a bearer token.
   - Use the same token for all three regional endpoints (contingent on Phase 0 confirming).
   - Defensively apply 1 req/sec rate limit (Ads-v1 rate limits are underdocumented).
   - Refresh on `401 Unauthorized`.
2. `ads.py`:
   - Fetch campaigns via `GET /v2/campaigns?state=enabled` to get a list of active campaign IDs
     and their metadata (name, country, budget currency).
   - For each campaign, request a daily report via
     `POST /v2/reports` with `reportDate={YYYY-MM-DD}` and dimensions
     `[date, adProduct]` to get spend by ad type (Sponsored Products, Sponsored Brands, etc.).
   - Poll `GET /v2/reports/{reportId}` until status = `COMPLETED`.
   - Download the report CSV and parse it; aggregate by date + ad product + campaign → totals.
   - Upsert into `ad_spend_daily` on `(marketplace_id, date, campaign_id, ad_product)`.
   - Map `adProduct.value` enum to P&L buckets:
     - `SPONSORED_PRODUCTS` → `advertising.sponsored_products`
     - `SPONSORED_BRANDS` → `advertising.sponsored_brands`
     - `SPONSORED_DISPLAY` → `advertising.sponsored_display`
     - `SPONSORED_TELEVISION` → `advertising.sponsored_television`
3. Write results to `pnl_monthly` and recompute Net Profit / Margin / ROI.

**DB tables touched:** `ads_reports`, `ad_spend_daily`, `pnl_monthly` (Advertising +
KPI rows).

**Acceptance check:** `reconcile.py` shows the Advertising bucket total matching the
sheet's `Sponsored brands + Sponsored display + Sponsored videos + Sponsored
television + Sponsored products` sum, and the combined `Sponsored brands + Sponsored
videos` sub-sum matches API `SPONSORED_BRANDS`.

---

## Phase 5 — Dashboard (US)

**Goal:** Next.js page that reproduces the reference sheet plus a sales trend line.

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
match the reference sheet (spot-check a few cells); the trend chart shows daily units and sales;
no request path touches Amazon.

---

## Phase 6 — Widen to CA, UK, AU

**Goal:** repeat Phases 1–4 for CA (NA / same SP token / CAD), UK (EU / `SP_REFRESH_TOKEN_EU` / GBP),
AU (FE / `SP_REFRESH_TOKEN_FE` / AUD).

**Steps:**

1. Region routing table in `sp_client.py`:
   ```
   {MARKETPLACE_ID_US} (US) → NA / SP_REFRESH_TOKEN_NA
   {MARKETPLACE_ID_CA} (CA) → NA / SP_REFRESH_TOKEN_NA
   {MARKETPLACE_ID_UK} (UK) → EU / SP_REFRESH_TOKEN_EU
   {MARKETPLACE_ID_AU} (AU) → FE / SP_REFRESH_TOKEN_FE
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
  diff CSV for the reference sheet.
- **Dashboard:** with the Next.js dev server running, `/pnl?marketplace=US` matches
  the reference sheet on spot-checked months; the trend chart renders.
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
- **COGS sheet data quality** — sync hard-fails on duplicate SKUs and requires clean input
  before processing.
- **COGS sheet formula cells** — safe because we read with `openpyxl(data_only=True)`, 
  which returns the cached numeric result. Must not open the workbook with `data_only=False` 
  in the sync.
- **Sales `getOrderMetrics` rate limit not stated** on the live reference — apply the
  0.5 rps SP-API-wide ceiling defensively.
- **AU COGS sheet column variation** — read by header name, not index.
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
| `reference/data/reference_sheet.xlsx` | ✅ inspected via openpyxl |
| `reference/data/cogs_workbook.xlsx` | ✅ inspected via openpyxl |
| `advertising.amazon.com/API/docs/*` | ❌ not retrievable (JS-gated; use `reference/ads-v1/` instead) |
| `github.com/amzn/ads-advanced-tools-docs` | ✅ noted as code-samples only (Postman collection is the useful artifact) |
| `github.com/amzn/selling-partner-api-models` | ✅ noted as authoritative schemas (not consulted this pass) |

These sources were fetched/read during planning. Phase 0 (ads header + token-region
probes) will append the two remaining probe results (accepted ClientId header per
endpoint; single-token region reachability) before Phase 4 begins.
