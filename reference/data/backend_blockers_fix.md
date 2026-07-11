# The three backend blockers — fixed, and what the fixing turned up

Run 2026-07-10. All three blockers (B1 `__main__.py` `KeyError`, B2 the missing ads loader, B3 the
stale `pnl_monthly` CA cog) are closed. B4 (AU had no `pnl_monthly` rows) closed as a consequence.

**Not one reported number moved.** All four reconcile reports are byte-identical to the golden
baseline once the `Generated` / `Prior pull` / `as_of` timestamp lines are excepted, and every numeric
token in them is identical, in order. Exit codes unchanged: US 1 (pre-existing, locked targets 9/15),
CA 0, UK 0, AU 0.

Two findings came out of the work that are more important than the fixes. Both are about **ingesting
new data**, and both are recorded in § 5.

---

## Step 0 — backups, taken before the first write

`reference/data/backups/`:

| file | rows | sha256 (head) |
|---|---:|---|
| `ad_spend_daily.csv` | 45,663 | `f233bdf92aff6b3c…` |
| `pnl_monthly.csv` | 696 | `f5433e8df7b4e05d…` |
| `TOTALS.txt` | per-marketplace/currency and per-bucket totals | — |
| `golden_reports/` | the four canonical reconcile reports | — |

`ad_spend_daily` was the only surviving output of a loader that no longer existed. Nothing was written
anywhere until these existed.

---

## Step 1 — `__main__.py:94`

`aggregate_marketplace` returns `transactions, leaves, mapped, unmapped_pairs, skipped_zero, pnl_rows,
fallback_txns, fallback_by_month`. It has never returned `groups`. The log line read
`agg_stats["groups"]`, so `python -m sync` raised `KeyError` after Phase 2 had committed its
`pnl_monthly` writes and before Phase 3 ran COGS — which is exactly how B3 was produced.

Fixed by reading the key that exists and matches the sentence:

```python
"Aggregate done: %d leaves → %d mapped, %d unmapped pairs, %d pnl rows",
agg_stats["leaves"], agg_stats["mapped"], ...
```

`aggregate.py`'s own summary already uses that vocabulary (`%d txns, %d leaves → %d mapped`). The
return shape was not touched.

All four marketplaces now run end to end:

| marketplace | leaves → mapped | unmapped pairs | pnl rows | COGS months | exit |
|---|---|---:|---:|---:|---:|
| US | 56,511 → 55,742 | 0 | 272 | 8 | 2 *(2 missing SKUs)* |
| CA | 2,276 → 2,085 | 0 | 162 | 7 | 0 |
| UK | 7,025 → 6,977 | 2 | 240 | 7 | 2 *(1 missing SKU + unmapped)* |
| AU | 1,886 → 1,856 | 0 | 139 | 7 | 0 |

Those non-zero exits are `__main__.py`'s documented `rc = 2` for unmapped leaves / missing SKUs, not
crashes. UK's 2 unmapped pairs are `Refund:Promo` (2 occurrences) — `Shipment.Promo` is routed to
passthrough but `Refund.Promo` falls through to `expenses`. Left alone: the bucket map is out of
scope, `expenses` reconciles inside its band, and no reported number moves.

**Phase 1 was deliberately a no-op** for these runs (`--start 2026-07-09T00:00:00Z`, past the
`now-48h` end, so `sync_marketplace` returns immediately) and Phase 1.5 was skipped. Ingesting new
Amazon data is a separate decision — see § 5.1.

---

## Step 2 — the ads loader, reproduced in committed code

### What was wrong

`ads_spend.py:140` dropped every row whose `budgetCurrency.value != "USD"`, then tagged the survivors
with whatever `--marketplace` said. Against CA it would `DELETE` the 2,213 real CAD rows for a month
and insert 5,642 USD rows — which `load_ad_spend` never selects, because it filters
`budget_currency = 'CAD'`.

### The fix

One NA report per month carries every marketplace; the rows are separated only by
`budgetCurrency.value`. So:

- `_parse_and_filter_usd` → `_parse_rows` (no filter).
- `_route_by_currency(rows, marketplace_ids)` splits by `budgetCurrency.value` using the inverse of
  `MARKETPLACE_AD_CURRENCY`: USD→US, CAD→CA, GBP→UK, AUD→AU. Anything it drops is logged — a silently
  dropped currency is how the rows went missing in the first place.
- `sweep_ad_spend` writes each marketplace from the one report, sharing **one `as_of` per month** —
  reproducing the microsecond-identical `as_of` across CA/UK/AU that the audit used as evidence that
  some other script had written them.
- `--marketplace ALL` regenerates every marketplace from one pull. `--table` points a run at a scratch
  copy. Default behaviour (`--marketplace US`, real table) is unchanged.
- `--batch-timeout-s` — see § 5.2.

`_replace_month`'s idempotent delete-then-insert and its `as_of` handling are untouched apart from
taking the table name.

### Verified three ways, against the backup — never against Sellerise

**1. Offline, from the archived raw reports.** The production `_parse_rows` + `_route_by_currency`
fed the four archived NA CSVs (`ads_probe_2026-0{1..4}_raw.csv`) reproduce the backup **exactly**, per
`(marketplace_id, date, campaign_id, ad_product)`, to the cent:

| month | USD→US | CAD→CA | GBP→UK | AUD→AU |
|---|---:|---:|---:|---:|
| 2026-01 | 5,642 | 2,213 | 1,704 | 1,778 |
| 2026-02 | 4,437 | 945 | 474 | 753 |
| 2026-03 | 4,872 | 94 | 198 | 62 |
| 2026-04 | 4,775 | 379 | 212 | 60 |

Every row count and every `total_cost` matched. (CA's 2026-01 total, £/$2,919.63, is the figure that
matches Sellerise to the cent.)

**2. Live, into a scratch table.** `--table ad_spend_daily_scratch --marketplace ALL`, Jan–Jun. Jan–May
reproduce the backup **exactly**. June does not — and that is not a loader defect, see § 5.2.

**3. Live, into the real table.** `--marketplace ALL --start 2026-01-01 --end 2026-05-31`, 5 months,
35,851 rows. Afterwards:

- Jan–May: **exact** match to the Step-0 backup, per PK, to the cent.
- June and US July: `9,812 / 9,812` rows with **amounts and `as_of` unchanged** — never touched.
- `ad_spend_daily`: 45,663 rows, same as the backup. Per-currency totals unchanged
  (USD 118,950.56 · CAD 8,493.08 · GBP 8,182.92 · AUD 3,562.57).
- The readers (`reconcile.py:336`, `reconcile_au.py:195`) select them with no change.

`ad_spend_daily` is no longer unreproducible state.

---

## Step 3 — `pnl_monthly` cog

**No code change was needed.** `cogs.py` already resolves `MARKETPLACE_COG_SOURCE_OVERRIDE`
(`cog_mp = cog_source_marketplace(...)`) and already writes `row_currency = cog_currency(...)` rather
than a hardcoded literal. The rows were stale purely because B1 killed the pipeline before Phase 3
ever ran. Fixing B1 fixed B3 on the next run.

`pnl_monthly.cog` now equals `reconcile.py`'s in-memory figure for **every marketplace and every
month**, Δ = 0.0000 throughout:

| marketplace | before | after | note |
|---|---:|---:|---|
| US | 191,284.87 (8 mo) | unchanged | control: was already correct |
| **CA** | **10,749.76** | **8,324.18** | −2,425.58 (−22.6 % of the stored value); the override now applied |
| **UK** | 18,435.56, labelled `USD` | same values, labelled **`GBP`** | S7 landed in `config.py` but `cogs.py` had never re-run |
| **AU** | **no rows at all** | **7 rows**, 14,195.72 | B4 closed |

CA's `currency` label stays `USD` and is now *truthful*: `cog_currency("CA")` resolves the override to
the US sheet, so the value really is USD-denominated. Before, the same label sat on a CAD-scale value.

`pnl_monthly_snapshots` was not rewritten — it only gained new `pull_at` batches, as designed.

---

## 5. What the fixing turned up

### 5.1 Running Phase 1 today would move reported numbers — with new Amazon data, not a regression

The pipeline is not a pure function of the rows already in `sp_transactions`; Phase 1 ingests. A
read-only probe pulled the exact window `python -m sync` would pull and diffed it against the database:

| marketplace | new txns | rows landing in Jan–Jun (new + changed) | existing rows whose JSON changed |
|---|---:|---:|---:|
| AU | 38 | 27 | 9 (all June) |
| UK | 35 | 17 | 3 (all June) |
| CA | 35 | 27 | 2 (all June) |

Most of the new in-window rows are `RELEASED` **release events**, which the pipeline correctly drops
(`is_deferred_release_event`). The ones that bite:

- **UK: one new `Refund`, posted 2026-07-04, on an order purchased 2026-01-18** (`4C-76GT-VAWZ`,
  1 unit). UK's refund-COGS basis is **purchase**, so it nets that unit out of **January's** cog:
  £3,388.38 → £3,381.68. January's pinned `cog.(scalar)` Δ would move 242.84 → 236.14. That is inside
  the ±25 tolerance, so the pin would hold — **by £18.30 of luck.** Had the refunded SKU been `ABDB`
  (£78.53), the pinned cell would have fired `INVESTIGATE`.
- **CA's 8 equivalent July-posted refunds of January orders are harmless**, because CA's refund-COGS
  basis is **posted** — their cog lands in July, outside the window.
- June moves for all four marketplaces.

**This is the finding, and it generalises:** `KNOWN_TARGET_DEFECT` pins a Δ measured against *both* a
frozen Sellerise snapshot *and* a frozen Amazon pull. Ingesting new Amazon data can move a pinned Δ
and fire `INVESTIGATE` on a cell where nothing is wrong. That is the pin behaving correctly — it
alarms on movement — but it means **"ingest" and "keep the guard green" are not independent
operations.** A re-pull should be a deliberate act, followed by re-deriving the pinned Δs. It must
never be a side effect of fixing a crash.

Hence Phase 1 was held to a no-op for every verification run here.

### 5.2 Amazon restates ads spend — measurably, at 3 days

June's ad rows did **not** reproduce the backup. The PK sets are identical (8,363 / 8,363); exactly
**8 rows** changed, every one revised **downward**:

| marketplace | date | adProduct | was | now | Δ |
|---|---|---|---:|---:|---:|
| UK | 2026-06-11 | Sponsored Products | 17.06 | 16.58 | −0.48 |
| US | 2026-06-24 | Sponsored Brands | 40.24 | 39.12 | −1.12 |
| US | 2026-06-25 | Sponsored Products | 65.16 | 63.37 | −1.79 |
| US | 2026-06-25 | Sponsored Products | 3.30 | 1.90 | −1.40 |
| US | 2026-06-25 | Sponsored Products | 1.40 | 0.00 | −1.40 |
| US | 2026-06-26 | Sponsored Products | 0.84 | 0.00 | −0.84 |
| US | 2026-06-28 | Sponsored Products | 59.41 | 57.91 | −1.50 |
| US | 2026-06-30 | Sponsored Brands | 13.80 | 13.51 | −0.29 |

Net: **US −$8.34, UK −£0.48**, between the 2026-07-07 pull and today. Nothing else in Jan–May moved by
a cent.

This is what `as_of` was built for — *"makes restatement drift distinguishable from a real pipeline
bug — the timestamp is the audit trail."* It also puts a number on a claim that previously rested on a
13-hour window: **Amazon's own ads restatement is real, it is confined to the trailing month, and at
3 days it is −$8.82 across 8 rows.**

Writing June would have moved `adExpenses` in the US and UK reports. Per the brief's operating rule,
it was **not written**. June's rows still carry their original `2026-07-07` `as_of`.

### 5.3 `sweep_ad_spend`'s 20-minute batch cap cannot pull January

2026-01 is the largest month (11,337 rows) and its report takes **~19 minutes** to generate — past the
hard-coded `deadline = time.time() + 20 * 60`. On the first scratch run January timed out and was
reported as `failed`.

It failed **safely**: `_replace_month` is only reached on `COMPLETED`, so a timed-out month is never
deleted. That is worth knowing and worth keeping.

Fixed with `--batch-timeout-s` (default `20 * 60`, unchanged), alongside the existing
`--submit-gap-s` / `--poll-round-s` tunables. January then completed in one attempt and reproduced the
backup exactly.

---

## Definition of done

| requirement | status |
|---|---|
| `python -m sync --marketplace {US,CA,UK,AU}` complete end to end, no `KeyError` | ✅ all four |
| `ads_spend.py` writes native-currency rows reproducing the backup **to the cent** | ✅ Jan–May exact, three independent ways |
| readers in `reconcile.py` / `reconcile_au.py` select them unchanged | ✅ no reader changed |
| `pnl_monthly` cog == reconcile's in-memory figure, correct `currency` labels | ✅ Δ = 0.0000, all 4 marketplaces, all months |
| four reports byte-identical to golden (timestamps excepted) | ✅ every numeric token identical, in order |
| exit codes unchanged (UK 0, AU 0, CA 0, US 1) | ✅ |
| backups written before the first mutation | ✅ `reference/data/backups/` |
| no snapshot history rewritten | ✅ append-only; only new `pull_at` batches |
| June ads **not** written (restated; would move reported numbers) | ✅ deliberately excluded |

## Code changed

Two files.

- `sync/__main__.py` — one log line: `agg_stats["groups"]` → `agg_stats["leaves"]`.
- `sync/ads_spend.py` — `_parse_rows` replaces `_parse_and_filter_usd`; `_route_by_currency` added;
  `sweep_ad_spend` takes `marketplace_ids` and writes each from one report under one `as_of`;
  `_replace_month` takes a `table` name; `--marketplace ALL`, `--table`, `--batch-timeout-s`.

Nothing else. No reconciliation math, no attribution, no bucket maps, no bands, no
`KNOWN_TARGET_DEFECT` registry, no schema, no `aggregate_marketplace` return shape.

## The one command that regenerates the ads table

```bash
python -m sync.ads_spend --marketplace ALL --start 2026-01-01 --end 2026-05-31 --batch-timeout-s 2700
```

Verify first, always:

```bash
python -m sync.ads_spend --marketplace ALL --start ... --end ... \
                         --table ad_spend_daily_scratch --batch-timeout-s 2700
# then diff ad_spend_daily_scratch against reference/data/backups/ad_spend_daily.csv
```
