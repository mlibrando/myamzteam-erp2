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

2. **Settled vs estimated is by `transactionStatus`, not by leaf name (probe-confirmed).**
   SP-API emits `Commission` and `FBAPerUnitFulfillmentFee` at *every* status. Sellerise's
   settled lines (`Commission` / `FBAPerUnitFulfillmentFee`) and its estimate lines
   (`ReferralFee` / `FBAFees`) are the **same leaves re-labelled by status**:
   - `RELEASED` **+ `DEFERRED_RELEASED`** → settled → `feesObject.Commission` /
     `fbaObject.FBAPerUnitFulfillmentFee`
   - `DEFERRED` only → pending estimate → `feesObject.ReferralFee` / `fbaObject.FBAFees`

   `DEFERRED_RELEASED` means *was deferred, now released* — it is **settled money** and is
   the dominant status (~4,590 occ vs ~411 for `DEFERRED`). Routing it to the estimate
   bucket would blow up every settled month. Older months are fully settled (estimate = 0);
   only the trailing live month carries `DEFERRED`. **Reconcile oldest→newest and expect
   only the trailing month's estimate lines to differ.**

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

## Step 1 — Probe (COMPLETE — do not re-run)

The breakdown-vocabulary probe is done: `reference/data/probe_breakdowns.md`, 129
`(txnType, txnStatus, breakdownType)` combos across 13,818 US transactions (Jan–Jul 2026).
**Every observed leaf is already accounted for — 0 unmapped.** Spelling resolved:
`Principal` (not `Principle`), universally. Treat that file as the authoritative leaf
inventory. Do not re-probe; the mapping decisions below are locked from it.

## Step 2 — Mapping decisions (LOCKED — implement, do not re-litigate)

These are resolved from the probe + the full 6-month Sellerise response. They are
authoritative. Where a validation target is given, assert it in the report.

**A. Status split (supersedes any earlier RELEASED-vs-DEFERRED wording).** Per Ground
truth 2.2: `RELEASED` + `DEFERRED_RELEASED` → settled buckets; `DEFERRED` only → estimate
buckets (`ReferralFee` / `FBAFees`). *Validate: Feb and Mar must yield
`feesObject.ReferralFee = 0` and `fbaObject.FBAFees = 0`.*

**B. SP-API `ProductAdsPayment.AdvertisingFee` (238 occ) → `passthrough`, excluded from
net.** Net's advertising comes from the five Ads-API lines only; counting this too would
double-count the same spend. Keep it as an audit line: in the report, diff its monthly
total against the Ads-API total as an independent cross-check. Never compare it to a
Sellerise bucket.

**C. Transaction-level fallback leaves (Shipment, 14 occ each) → the real fee buckets.**
`AmazonFees(Shipment)` → `feesObject.Commission`; `FBAFees(Shipment)` →
`fbaObject.FBAPerUnitFulfillmentFee`. These are parent roll-ups the flattener emits when
`items[]` yields only `Base` roots. **Fix the current bug:** `AmazonFees` today routes to
`other_amz.amazon_fees` (the excluded expenses bucket), which understates net fees. Apply
the status split from A (a fallback at `DEFERRED` → `ReferralFee`). Log `transactionId`
whenever the fallback fires.

**D. Refund components `RestockingDeduction*` / `Goodwill*` → `refundsObject`, NOT
expenses.** (They were absent in March, which is why they looked unplaced.)
- `RestockingDeductionPrincipal` + `RestockingDeductionTax` → `refundsObject.RestockingFee`
  (sum both into the one line; positive = fee retained, reduces refund cost).
  *Targets: Feb +52.94, Apr +4.59, Jun +9.70.*
- `GoodwillPrincipal` → `refundsObject.Goodwill` (negative concession).
  *Targets: May −17.09, Jun −13.23.* Validate against **June** (both non-zero).

**E. Shipment `Promo` (positive, 8 occ) → `passthrough`, excluded, uncompared.**
Validated by arithmetic: Feb `refundsObject.Promotion` = 146.99 = `Refund.OurPriceDiscount`
+ `Refund.ShippingDiscount` *exactly* — Sellerise builds that bucket from the two Refund
discount leaves and does **not** include `Shipment.Promo`. So `Shipment.Promo` has no home
in the Sellerise net taxonomy; treat it like `AdvertisingFee`/MFT (real money Sellerise's
P&L doesn't count). Do NOT route it to `refundsObject.Promotion` (overshoots by the Promo
amount) or `chargesObject.Promotion` (would inflate revenue).
Map the actual promotion lines instead: `Refund.OurPriceDiscount` + `Refund.ShippingDiscount`
→ `refundsObject.Promotion`; the negative charge-side promotion leaf → `chargesObject.Promotion`
(confirm its exact name from `probe_breakdowns.md`).
*Targets — `refundsObject.Promotion`: Feb 146.99, Mar 44.87, Jun 3.99; `chargesObject.Promotion`:
Feb −811.14, Mar −610.03, Jun −496.12.* (`promos = −Promotion` is derived — don't source it
separately. Small remaining charge-side deltas are DEFERRED-timing residuals, not Promo.)

**F. `MarketplaceFacilitator*` / `VAT*` / `LowValueGoodsTax-*` at Shipment → `passthrough`,
excluded, uncompared.** Collect+remit net-zero with no Sellerise home. `salesTaxes` is
**derived** (`Tax + ShippingTax + GiftWrapTax`), not sourced from facilitator leaves, and
`chargesObject.Tax` = `OurPriceTax` alone (Mar 6,673.91). Map only `OurPriceTax` →
`chargesObject.Tax`, `ShippingTax` → `ShippingTax`, `GiftwrapTax` → `GiftWrapTax`.

**G. Three-way inclusion flag with fixed precedence.** Every leaf resolves to
`net | expenses | passthrough`, keyed by `(txn_type, breakdown_type, txn_status)`.
Resolve in this order:
1. `passthrough` — MFT*/VAT*/LowValueGoodsTax*, `ProductAdsPayment.AdvertisingFee`,
   `Shipment.Promo`
2. explicit `net` buckets — `chargesObject` / `feesObject` / `fbaObject` / `refundsObject` /
   `storageFee` (`salesTaxes` is derived, not sourced; `adExpenses` is Ads-API)
3. `expenses` — the remainder (mirrors Sellerise's own catch-all `expenses` object)

Precedence matters: resolve passthrough *first* or MFT/AdvertisingFee leaves fall into
`expenses`. Guard: a genuinely new/unknown leaf raises an **unmapped WARNING and defaults
to `expenses`** (safe — kept out of net), so you're alerted without corrupting net.

## Step 2 (impl) — rewrite `bucket_map.py`

Flattener (small, defensive — handles both breakdowns shapes; see Gotchas):

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

Then bucket each leaf using the mapping keyed by `(txn_type, breakdown_type, txn_status)`,
carrying the `net | expenses | passthrough` flag from decision G. Aggregate into the
Sellerise buckets per month (`postedDate`). The full leaf inventory lives in
`reference/data/probe_breakdowns.md`; decisions A–G above are the only deltas from today's
`BUCKET_MAP`. This is a mechanical rewrite — the map already covers every observed leaf.

## Step 3 — Reconciliation report

Read `reference/data/SELLERISE_RAW_DATA.json` and produce a per-month, per-bucket
comparison of our computed numbers vs Sellerise, for `chargesObject`, `feesObject`,
`fbaObject`, `refundsObject`, `salesTaxes`, `storageFee`, the excluded `expenses` bucket,
`adExpenses`, and `net`. For each cell show ours, theirs, and the delta. Use a small
tolerance (e.g. ±$0.01) and mark PASS/FAIL. Order months oldest→newest; treat the trailing
month's `DEFERRED` estimate lines as expected mismatches, not failures.

Assert the locked validation targets so a regression is caught immediately:
- Feb & Mar: `feesObject.ReferralFee = 0`, `fbaObject.FBAFees = 0` (decision A).
- `refundsObject.RestockingFee`: Feb 52.94, Apr 4.59, Jun 9.70 (D).
- `refundsObject.Goodwill`: May −17.09, Jun −13.23 (D).
- `refundsObject.Promotion`: Feb 146.99, Mar 44.87, Jun 3.99 (E).
- `chargesObject.Promotion`: Feb −811.14, Mar −610.03, Jun −496.12 (E).

Also emit the audit cross-check (decision B): SP-API `AdvertisingFee` monthly total vs the
Ads-API monthly total — informational, not a PASS/FAIL gate.

Any leaf `breakdownType` seen in the data but not in the mapping must surface as an
"unmapped" WARNING (and default to `expenses`), never silently dropped.

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
- `bucket_map.py` implements decisions A–G, keyed by `(txn_type, breakdown_type, txn_status)`
  with the `net | expenses | passthrough` flag and passthrough-first precedence.
- For fully-settled months, every Sellerise bucket AND `net` reconcile within ±$0.01, and
  all locked validation targets (Step 3) pass.
- Only the trailing `DEFERRED` month shows deltas, isolated to the estimate lines.
- No leaf is dropped without an unmapped WARNING; unknown leaves default to `expenses`.