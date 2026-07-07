# Claude Code Task — Phase 4: Ads spend → net reconciliation (verify our data first)

## Context

Revenue-side is reconciled after the purchase-date pass (cumulative Principal −0.03%). The
only remaining net gap is that `adExpenses` is 0 in ours, leaving net ~$18k/month too high.
Populating the five ad lines *should* close it — but that is a **prediction to verify, not
an assumption to build on.**

We already hold the reconciliation target: `reference/data/SELLERISE_RAW_DATA.json` contains
Sellerise's exact monthly ad numbers per line for Jan–Jun — `adCost` (Sponsored Products),
`hsaCost` (Sponsored Brands), `hsaVideoCost` (Sponsored Brands Video), `sdCost` (Sponsored
Display), `stvCost` (Sponsored TV). Reconcile the Ads-API pull **against these**; don't fetch
and trust.

Ads Reporting API v1 (unified): `POST /adsApi/v1/create/reports` → poll
`POST /adsApi/v1/retrieve/reports` → download `completedReportParts` (presigned S3). Spend =
`metric.totalCost`; product split via `adProduct.value`.

## Operating rules

- **Verify on our end before assuming shape or structure.** Pull one real report for one
  settled month and observe what actually comes back *before* writing integration code or
  hard-coding any enum, denomination, or date behavior. The project docs describe the flow;
  they do **not** substitute for seeing our account's actual data.
- Minimalist: a pipeline that produces five monthly ad numbers and subtracts them into net.
  No new dependencies beyond the Ads report flow. Reuse existing Ads auth/refresh.
- Measure before/after and report numbers. Don't widen tolerance to force net closure.

## The two things that MUST be verified empirically (priority)

### V1 — Line-sum parity: does our spend match Sellerise's?
Reconcile per month (Jan–Jun) against the Sellerise ad lines in `SELLERISE_RAW_DATA.json`.

- **PRIMARY (this is what closes net):** total monthly Ads-API spend, summed over *all*
  `adProduct` values, must equal Sellerise's summed five lines
  (`adCost+hsaCost+hsaVideoCost+sdCost+stvCost`) within a small tolerance. Net only needs the
  **total**, so this is the real target.
- **SECONDARY:** match each of the five lines individually. Expect a structural obstacle:
  `adProduct.value` likely exposes only `SPONSORED_PRODUCTS` / `SPONSORED_BRANDS` /
  `SPONSORED_DISPLAY` / `SPONSORED_TELEVISION` — **no distinct Brands-Video value.** So
  `hsaCost` vs `hsaVideoCost` may not be separable on `adProduct` alone. Verify whether *any*
  dimension (cost type, ad format, creative type) splits SB Video from SB. **If not separable,
  merge `hsaCost+hsaVideoCost` into one `SPONSORED_BRANDS` line, document it, and rely on the
  total for net** — the split does not affect net.

### V2 — Spend date basis: does our month boundary match Sellerise's?
Determine which date the Ads API attributes **spend** (`metric.totalCost`) to, and whether
bucketing by that date's month reproduces Sellerise's monthly totals.

- Request `date.value` + `adProduct.value` + `metric.totalCost` daily, bucket by month,
  compare to Sellerise per month. If a month is off by ~one boundary day's spend, that's a
  date-basis / timezone effect analogous to the 48h P&L cutoff — **measure it, don't assume
  it's zero.**
- Verify restatement behavior: Ads reporting can restate for a few days, so recent months may
  move. Reconcile **settled (older) months first**, exactly as on the P&L side.

## Step 1 — Probe one real report (observe before building)

- Resolve the US `advertiserAccountId` (`POST /adsAccounts/list`).
- Create a minimal report for ONE settled month: fields `date.value`, `adProduct.value`,
  `metric.totalCost` (add `budgetCurrency.value` only if `totalCost` requires it — **verify**;
  `metric.sales` requires currency but `totalCost` is a traffic metric and may not). Run the
  full create→poll→retrieve→download flow; handle `PENDING`/`PROCESSING`/`COMPLETED`/`FAILED`.
- Record from the actual response, do not assume:
  - the exact `adProduct.value` strings returned, and whether SB Video appears anywhere;
  - how `metric.totalCost` is denominated — **currency units vs micros** (this is a classic
    silent 1,000,000× bug; confirm against a known Sellerise monthly figure);
  - the currency and row shape;
  - which auth header the endpoint actually accepted (memory flagged an
    `Amazon-Ads-ClientId` vs `Amazon-Advertising-API-ClientId` contradiction — record the
    one that worked), and that account-based `accessRequestedAccounts` is correct for this
    endpoint vs a profile scope.
- Dump distinct `adProduct` values + a sample of rows to a scratch file and stop to confirm
  before building the full pull.

## Step 2 — Build the monthly-spend pull

- Pull Jan 2026 → now with `date.value` + `adProduct.value` + `metric.totalCost`. Poll ~1/min;
  download parts (handle `PARTITIONED_*` if large). Aggregate to `{month, adProduct} →
  totalCost`.
- Map to the five Sellerise lines per V1 (SB Video merged into SB if not separable). US only,
  USD, no FX. Persist monthly ad spend.

## Step 3 — Reconcile ad lines, then wire into net, then re-run

- **First** reconcile the ad lines alone against Sellerise (emit the V1 and V2 tables): per
  line and total, per month, ours vs Sellerise vs delta.
- **Only once** total monthly spend matches Sellerise within tolerance for settled months,
  subtract `adExpenses` into net in `reconcile.py` and re-run the full report.
- Emit **net before/after**: the net gap per month with `adExpenses=0` vs with real spend, vs
  Sellerise. Confirm the ~$18k/month closes. If it doesn't fully close, report the residual by
  line — do not assume it's the ad total; it could be the V2 boundary effect or a product the
  Ads API attributes differently.
- Triangulate (informational only): the SP-API `AdvertisingFee` audit line already in the
  report (~$20k/mo) vs Ads-API total vs Sellerise total — three sources for the same money.
  They will **not** match exactly (SP-API billing is timing/subset-different); expect
  same-order-of-magnitude, not parity.

## Guardrails / accepted residuals

- Nothing about the `adProduct` enum, the `totalCost` denomination, or SB/Video separability is
  assumed — all are established in Step 1 against real data.
- Merging SB Video into SB is acceptable and does not affect net — document it, don't force a
  split the API can't produce.
- Restatement + any boundary-day effect are analogous to the 48h P&L cutoff: measure, document
  as accepted residual, reconcile older months first.
- Don't widen tolerance to force net closure; leave residuals visible in the report.

## Definition of done

- Step-1 probe recorded: actual `adProduct` values, `totalCost` denomination, currency, auth
  header used, and the SB-Video separability answer.
- Monthly Ads spend pulled Jan→now (five lines, SB Video merged if needed), persisted.
- V1 and V2 answered with numbers: total monthly spend within tolerance vs Sellerise for
  settled months; per-line parity where achievable; date-basis effect quantified.
- `adExpenses` wired into net; report re-run; the ~$18k/month net gap closed for settled months
  (or the residual explained by line).
- The basis choice and any residual (SB-Video merge, boundary day, restatement) documented as
  design decisions.