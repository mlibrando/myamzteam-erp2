# Claude Code Task — SP-API ↔ Sellerise P&L Reconciliation Layer

## Context

We're building the MYAMZTEAM ERP (Amazon P&L automation), US marketplace first.
Stack: FastAPI backend, Next.js dashboard, PostgreSQL on Railway, Railway cron for syncs.

Phases 0–3 are already built: auth/refresh tokens, SP-API `listTransactions` fetch,
Ads API spend fetch, and persistence. **This task has two parts:** (1) refactor the
SP-API fetch/auth layer onto the `python-amazon-sp-api` library (see Step 0), and
(2) build the reconciliation layer that makes our computed monthly P&L match Sellerise's
numbers to the cent for settled months. The reconciliation is the tricky part; the
library refactor is plumbing that simplifies the fetch/auth/pagination code but changes
nothing about the reconciliation logic.

Everything below marked "verified" was reverse-engineered from Sellerise's actual API
response (Jan–Jun 2026, `group=month`) and confirmed to the cent, plus a real
`listTransactions` sample response. Treat it as ground truth. Do not re-derive it.

## Operating rules (non-negotiable)

- Consult official Amazon docs for anything not stated here. **Never assume** API
  behavior — when a value, field name, or schema shape is uncertain, **probe the real
  account empirically** and flag anything you could not verify.
- **Minimalist engineering.** Simplest, most readable, most robust solution. No
  speculative helpers, no premature abstraction. Solve exactly this. The **one sanctioned
  new dependency is `python-amazon-sp-api`** (used for the fetch/auth layer, Step 0); do
  not add others without asking.

---

## Ground truth 1 — Sellerise's P&L math (verified across all 6 months)

Sellerise returns per-month objects. Its numbers are pure roll-ups:

```
revenue    = Σ chargesObject                      (Promotion is stored negative)
promos     = −Promotion
salesTaxes = Tax + ShippingTax + GiftWrapTax      (from chargesObject)
fees       = −Σ feesObject
fba        = −Σ fbaObject
refunds    = −Σ refundsObject
storageFee = monthly FBA storage (separate top-level line)
cog        = from COGS workbook (NOT SP-API)

net = revenue − salesTaxes − fees − fba − refunds − storageFee − cog
      − (adCost + hsaCost + hsaVideoCost + sdCost + stvCost)
```

Ad line meanings: `adCost`=Sponsored Products, `hsaCost`=Sponsored Brands,
`hsaVideoCost`=Sponsored Brands **Video** (kept SEPARATE — do not fold into SB),
`sdCost`=Sponsored Display, `stvCost`=Sponsored TV. All are Ads API `metric.totalCost`
split by `adProduct.value`.

## Ground truth 2 — three rules that are almost certainly why reconciliation fails

1. **The `expenses` bucket is EXCLUDED from Sellerise's net.** Inbound transportation,
   reimbursements, clawbacks, `StorageRenewalBilling`, removals, disposals, warehouse
   lost/damage, subscription fee, etc. — none of it is in `net` (it was −9,743.45 in Jan,
   simply omitted). **To match Sellerise's net, we must also exclude these transactions
   from our net.** Keep them stored/visible as their own bucket, but out of the net total.
   (For a "true" P&L they are real costs — make this an explicit, configurable exclusion,
   not a silent one.)

2. **Deferred = estimated, Released = settled.** Sellerise splits fees: settled amounts
   land in `Commission` / `FBAPerUnitFulfillmentFee`; its *estimates* for orders not yet
   posted land in generic `ReferralFee` / `FBAFees`. Older months (Jan–Apr) are fully
   settled with ~zero estimate; recent months (May, Jun) carry large estimates. This maps
   directly to `transactionStatus` RELEASED vs DEFERRED. **Reconcile oldest→newest and
   expect the trailing 1–2 months not to match to the cent until they settle.**

3. **`storageFee` ≠ `StorageRenewalBilling`.** The monthly storage fee is its own line and
   IS in net. `StorageRenewalBilling` (long-term storage) is in the EXCLUDED expenses
   bucket. Do not conflate.

Also: tax is pass-through — collected inside `revenue` and removed via `salesTaxes`, net
zero to profit. Mirror that (don't drop tax from revenue, subtract `salesTaxes`).

## Ground truth 3 — SP-API `listTransactions` structure (v2024-06-19)

- **`breakdowns` is a RECURSIVE TREE**, not a flat list. Each node = `{breakdownType,
  breakdownAmount{currencyAmount,currencyCode}, breakdowns[]}`. Charges nest e.g.
  `Sales → Product Charges → Principal`. You must walk to the leaves and sum them.
- `postedDate` → the month-bucket key. Bucket on this.
- `transactionType` (e.g. `Shipment`, `Refund`) + `description` (e.g. `Order Payment`)
  → route a transaction to the right Sellerise bucket.
- `transactionStatus` (`Released` / `Deferred`) → the settled-vs-estimated lever.
- `items[].contexts[]` `ProductContext` gives `sku`, `asin`, `quantityShipped`
  → COGS join key + per-unit multiplier.

---

## Step 0 — Refactor the SP-API fetch/auth layer onto `python-amazon-sp-api`

Replace the hand-rolled auth + raw HTTP calls with this library for all SP-API access.
It's actively maintained (v2.1.8, Feb 2026, MIT, httpx-based) and supports the exact
endpoint we need. Scope of this refactor is fetch/auth/pagination/throttling ONLY — it
does not touch reconciliation.

- Install: `pip install python-amazon-sp-api`.
- Use `sp_api.api.FinancesV20240619`. The call is:

  ```python
  from sp_api.api import FinancesV20240619
  from sp_api.base import Marketplaces

  resp = FinancesV20240619(marketplace=Marketplaces.US).list_transactions(
      postedAfter=start_iso, postedBefore=end_iso, transactionStatus="RELEASED",
  )
  payload = resp.payload            # -> {"nextToken": ..., "transactions": [...]}
  transactions = resp.payload.get("transactions", [])
  ```

- **Regional routing is handled by the `Marketplaces` enum** (`Marketplaces.US`, `.CA`,
  `.UK`, `.AU`) — one client instance per marketplace, no hand-maintained host tables.
  This is how we expand past US.
- **Auth:** the library performs the refresh-token → access-token exchange itself
  (credentials via env vars, config file, or code). Delete the custom auth/token code.
- **Pagination:** loop on `resp.next_token` (a first-class `ApiResponse` attribute) or
  wrap the call with the library's `load_all_pages` decorator. Parse target is always
  `resp.payload`.
- **Throttling:** `resp.rate_limit` exposes the `x-amzn-RateLimit-Limit` header; pace the
  backfill off it (listTransactions is 0.5 rps). The library also provides retry
  decorators for 429s.
- **The library returns the RAW Amazon payload — it does NOT model `breakdowns`.** You
  still get the same nested tree (with the `"Principle"` spelling and object/array shape
  quirks below), so the flattener, mapping, and reconciliation in Steps 1–3 are unchanged.

**Verify before wiring in** (docs only show `list_transactions(**kwargs)`, params not
enumerated): (a) the exact kwarg casing — `postedAfter` (camelCase passthrough) vs a
snake_case variant — by checking `sp_api/api/finances/finances_v2024_06_19.py` or one
sandbox call; (b) that `load_all_pages` keys off this endpoint's `nextToken`, since token
field names vary across SP-API endpoints. Flag whichever you couldn't confirm.

## Step 1 — Run an empirical probe BEFORE writing the mapping

Use the Step 0 client for this. We do NOT have the full leaf `breakdownType` vocabulary,
and the sample response has two traps (see Gotchas). So discover it from the real account
instead of hardcoding:

- Call `FinancesV20240619(...).list_transactions(...)` for the US marketplace over a
  settled window (e.g. a full past month), once per `transactionType` present, and dump
  the **distinct leaf `breakdownType` values** (with a couple of example amounts each) to
  a scratch file.
- From that output, resolve: the exact spelling of the principal line, the actual
  `breakdownType` strings for referral fee, FBA per-unit fee, shipping chargeback,
  gift-wrap, marketplace-facilitator tax, refund components, storage fee, and each
  `expenses`-bucket item.
- Print the findings and stop for review before locking the mapping. Flag any leaf you
  cannot confidently assign to a Sellerise bucket.

## Step 2 — Flattener + bucketer

Small and defensive. Handle both breakdowns shapes (see Gotchas):

```python
def leaf_breakdowns(node):
    # node may be a list, or an object wrapping {"breakdowns": [...]}
    items = node.get("breakdowns", []) if isinstance(node, dict) else node
    for b in items or []:
        kids = b.get("breakdowns") or []
        if kids:
            yield from leaf_breakdowns(kids)
        else:
            yield b["breakdownType"], b["breakdownAmount"]["currencyAmount"]
```

Then, using the probe-confirmed mapping `{breakdownType: sellerise_bucket}`, aggregate each
transaction's leaves into the Sellerise buckets, keyed by month (`postedDate`) and by
`transactionStatus`. Keep settled and deferred separated so we can reproduce both the
settled figure and Sellerise's estimate behavior.

## Step 3 — Reconciliation report

Produce a per-month, per-bucket comparison of our computed numbers vs the Sellerise
response, for `chargesObject`, `feesObject`, `fbaObject`, `refundsObject`, `salesTaxes`,
`storageFee`, the excluded `expenses` bucket, `adExpenses`, and `net`. For each cell show
ours, theirs, and the delta. Use a small tolerance (e.g. ±$0.01) and mark PASS/FAIL.
Order months oldest→newest; treat the trailing months' fee estimates as expected
mismatches, not failures. Any leaf `breakdownType` seen in the data but not in the mapping
must surface as an "unmapped" warning line, never silently dropped.

---

## Gotchas (confirm each during the probe)

- **Schema shape mismatch.** The API reference types `Transaction.breakdowns` as a
  `Breakdown` array, but the sample wraps it as `{"breakdowns": [...]}`, while
  *item-level* breakdowns is a bare array. Parse both (the flattener above does).
- **Spelling.** The sample literally shows `"Principle"` (misspelled). If the live API
  returns that, a hardcoded `Principal` silently drops the largest revenue line. Use the
  probe's real value; don't trust either spelling.
- **Status casing.** You SEND `RELEASED` but the response RETURNS `Released`. Compare
  case-insensitively.
- **180-day window.** `postedAfter`/`postedBefore` >180 days apart returns empty — chunk
  the Jan-2026-forward backfill into ≤180-day windows per marketplace.
- **48-hour lag.** Financial events may exclude the last ~48h — the current day or two is
  always incomplete; don't reconcile it.

## Non-SP-API inputs (don't chase these in listTransactions)

- `cog` → COGS workbook (`COGS_Magical_Butter`), joined on SKU with ASIN fallback,
  native currency, × `quantityShipped`.
- `adExpenses` → Ads API, `metric.totalCost` split by `adProduct.value`, five lines as
  above (SB Video kept separate).

## Definition of done

- SP-API access goes through `python-amazon-sp-api` (`FinancesV20240619.list_transactions`),
  with the old hand-rolled auth/HTTP removed and the kwarg-casing + pagination checks resolved.
- For fully-settled months, every Sellerise bucket AND `net` reconcile within ±$0.01.
- The trailing unsettled month(s) show explainable deltas isolated to the fee-estimate
  lines, with a note in the report.
- No leaf `breakdownType` is dropped without an explicit unmapped-warning.
- The mapping dict is grounded in the probe output, with any unverified assignment flagged.