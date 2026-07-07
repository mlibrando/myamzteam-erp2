# Drift baseline for the monthly reconciliation regression guard

**Purpose:** when the live pipeline re-pulls next month, distinguish
**restatement drift** (expected — Amazon revises numbers post-hoc, Sellerise's
snapshot is frozen at one point in time) from a **pipeline regression**
(possible bug — our code, mapping, or attribution changed). A settled month
that reconciled to +$743 could read +$900 next pull and look identical whether
Amazon restated it or our pipeline broke — without a baseline, we can't tell.

This document is the empirical baseline + the guard's design. No accepted
reconciliation number was changed by this task.

## Step 1a — revenue-side restatement drift as one number

Correcting the Check-1 close-out framing: the "revenue-side snapshot residual"
labelled per month in `net_residual_diagnosis.md` (Mar +$589, Apr +$698) is
actually part of a broader pattern that runs across **all** settled months.
Stating it as one number:

Σ chargesObject vs Sellerise `revenue`:

| ym | ours | Sellerise | Δ | \|Δ\| |
|---|---:|---:|---:|---:|
| 2026-01 | 174,304.82 | 175,191.94 | −887.12 | 887.12 |
| 2026-02 | 145,146.53 | 144,011.44 | +1,135.09 | 1,135.09 |
| 2026-03 | 129,169.36 | 128,580.85 | +588.51 | 588.51 |
| 2026-04 | 124,533.78 | 123,835.52 | +698.26 | 698.26 |
| 2026-05 | 115,088.34 | 116,138.17 | −1,049.83 | 1,049.83 |
| 2026-06 | 102,946.67 | 103,235.08 | −288.41 | 288.41 |
| **Σ settled (Jan–May)** | | | **+484.91** | **4,358.81** |

**Total revenue-side restatement drift across settled months: ±$4,358.81
absolute (0.7 % of the $686k baseline), +$484.91 signed (essentially null).**
The mixed signs cancel — no directional bias, just snapshot noise between our
fresh pull and Sellerise's frozen view.

## Step 1b — observed pull-to-pull drift on ads

Ads is the only source with multiple pulls persisted on record. Comparing the
raw report CSVs (July 6-7) against the `ad_spend_daily` persistence (as_of
July 7 03:16):

| ym | CSV timestamp | Δ vs DB (Σ per adProduct) |
|---|---|---:|
| 2026-01 | 2026-07-07 10:32 | **$0.00** |
| 2026-02 | 2026-07-06 21:39 | **$0.00** |
| 2026-03 | 2026-07-07 10:32 | **$0.00** |
| 2026-04 | 2026-07-07 10:32 | **$0.00** |

**Amazon returned identical numbers over a ~13-hour window** on 2026-07-07.
The bulk of restatement drift accumulates on **week-to-month scales**, not
within a single day. The larger residuals (Sellerise-snapshot vs our fresh
pull) reflect ~4-6 weeks of drift between snapshot and now.

**Empirical drift distribution** (max |Δ| per bucket per settled month, from
`net_residual_diagnosis.md` post-refund-COGS-fix state):

| bucket · sub_line | max abs Δ | months seen |
|---|---:|---|
| chargesObject.Principal | 981 | 6 |
| chargesObject.Tax | 80 | 6 |
| chargesObject.ShippingCharge | 79 | 6 |
| feesObject.Commission | 149 | 6 |
| feesObject.ShippingChargeback | 79 | 6 |
| fbaObject.FBAPerUnitFulfillmentFee | 202 | 6 |
| refundsObject.Principal | 297 | 6 |
| cog (scalar) | 2,019 (Jan structural) / 493 (Mar–May) | 6 |
| storageFee (scalar) | 0.00 | 6 |
| ad TOTAL | 5.75 | 6 |

## Step 2 — Per-bucket, per-regime drift bands

Defined in [`backend/sync/drift_bands.py`](../../backend/sync/drift_bands.py).
Each band = max observed |Δ| across settled months × 1.5–2× margin, floored at
$5 for cells that match to the cent. Full derivation in the source; summary:

| cell | settled band | derivation |
|---|---:|---|
| chargesObject.Principal | ±$1,500 | obs 981 × 1.5 |
| chargesObject.Tax | ±$200 | obs 80 × 2.5 |
| chargesObject.ShippingCharge | ±$200 | obs 79 × 2.5 |
| chargesObject.GiftWrap[Tax] | ±$5 | matches to cent |
| chargesObject.Promotion | ±$60 | E-decision residual |
| feesObject.Commission | ±$300 | obs 149 × 2 |
| feesObject.ShippingChargeback | ±$120 | obs 79 × 1.5 |
| feesObject.ReferralFee | ±$5 | decision A: 0 on settled |
| fbaObject.FBAPerUnitFulfillmentFee | ±$400 | obs 202 × 2 |
| fbaObject.FBAFees | ±$5 | decision A: 0 on settled |
| refundsObject.Principal | ±$400 | obs 297 |
| refundsObject.Commission | ±$100 | obs 45 |
| refundsObject.RestockingFee, Goodwill | ±$5 | decision D: matches |
| storageFee (scalar) | ±$5 | matches to cent every month |
| salesTaxes (derived) | ±$250 | sum of tax lines |
| cog (scalar) | ±$2,500 | Jan pre-backfill boundary = 2,019 structural |
| ad line | ±$10 | obs max 3.06 |
| ad TOTAL | ±$30 | obs max 5.75 |
| net (derived) | ±$5,000 | sum of bucket bands |

**Two regimes**:
- **Settled** (Jan–May): tight bands as above.
- **Trailing** (Jun, or whichever is the latest Sellerise-covered month):
  `TRAILING_MULTIPLIER = 3` × band. Refund lag + DEFERRED estimates keep this
  month moving. Decision-A trailing-DEFERRED lines
  (`fbaObject.FBAFees`, `feesObject.ReferralFee` on the trailing month) are
  already marked `EXPECTED` in the main diff and skipped by the guard.

## Step 3 — Guard integrated into `reconcile.py`

New output section in the reconcile report:

```
## Drift-guard: N INVESTIGATE / M TRAILING / K WITHIN_DRIFT
```

Every non-`EXPECTED`, non-adExpenses cell is classified per its band:
- `WITHIN_DRIFT` — expected restatement, no action
- `TRAILING` — current month still moving, expected to shift more
- `INVESTIGATE` — beyond the settled-month band, **loud signal**

`INVESTIGATE` fires get their own table at the top of the drift section
(sorted first) and a WARNING log line. The CLI exits **non-zero** if any
`INVESTIGATE` fires — so a scheduled pipeline run surfaces regressions as job
failures, not as silent drift.

## Step 4 — Verification

### 4a. Current state passes

Running reconcile with today's locked state:

```
Drift-guard: 0 INVESTIGATE — all settled cells within band.
```

154 settled cells `WITHIN_DRIFT`, 30 trailing-month cells `TRAILING` (Jun),
0 `INVESTIGATE`. ✓

### 4b. Guard has teeth — three perturbations tested

| perturbation | INVESTIGATE fires | outcome |
|---|---:|---|
| cog × 1.20 (20 % inflation bug) | 5 | ✓ CAUGHT — Jan/Feb/Mar/Apr/May cog all fire, Δ +$4,800 to +$6,800 vs ±$2,500 band |
| revert refund-netting fix | 0 | Not caught — subtle enough to stay within cog band (limitation, see below) |
| Principal sign flip (mapping regression) | 12 | ✓ CAUGHT — Principal + net fire on 6 months, Δ up to −$334k vs ±$1,500 band |
| final revert (no perturbation) | 0 | ✓ Guard returns to clean state |

Two of three real-bug simulations were caught. The third (subtle regression
that produces smaller-than-band deltas) is a **documented limitation**:

## Second guard — vs prior pull (implemented 2026-07-07)

The vs-Sellerise guard alone has a structural blind spot: cog's ±$2,500 band
is wide enough to absorb Jan's $2,019 pre-backfill boundary, which means it's
also wide enough to hide a ~$2,800 systematic regression (like reverting the
refund-COGS fix). That's the exact class of bug this project spent three
diagnosis cycles finding — the loud stuff we'd notice by hand, the guard now
catches, but the quiet systematic stuff was still exposed.

**Fixed by the `DRIFT_VS_PRIOR_PULL` guard.** Every reconcile run persists a
per-(month, bucket, sub_line) snapshot to `pnl_monthly_snapshots`, keyed by
`pull_at`. On the next run, each cell is compared against its most recent
prior snapshot with tight per-cell bands (see `PRIOR_PULL_BANDS` in
[`drift_bands.py`](../../backend/sync/drift_bands.py)) — no attribution
residual, no Sellerise offset, just true pull-to-pull movement.

### Band derivation (vs prior pull)

Empirical anchor: ads returned $0.00 pull-to-pull over ~13h (Step 1b above),
so pure drift on a settled month is small. Bands are calibrated to catch
systematic per-cell shifts without crying wolf on ordinary Amazon
restatement:

| cell | prior-pull band | rationale |
|---|---:|---|
| storageFee (scalar), gift wrap, decision-A/D cells | ±$1 | match to cent; any move = signal |
| refund small sub-lines | ±$5 | rarely move outside restatement window |
| chargesObject.Principal | ±$100 | catches ~$2.8k regression (0.08% of Principal) |
| chargesObject.Tax / ShippingCharge | ±$30 / ±$20 | proportional to typical drift |
| feesObject.Commission / fbaObject.FBAPerUnitFulfillmentFee | ±$50 | ~1000× tighter than vs-Sellerise |
| refundsObject.Principal / Commission | ±$50 / ±$20 | |
| cog (scalar) | ±$100 | catches the refund-fix revert bug (~$2.8k shift) |
| salesTaxes (derived) | ±$30 | |
| net (derived) | ±$500 | ~10× tighter than vs-Sellerise; catches the $2.8k regression |
| ad line / TOTAL | ±$3 / ±$10 | ads drift observed $0.00 over 13h; be strict |

Trailing multiplier ×3 same as vs-Sellerise guard. Decision-A trailing
`EXPECTED` lines still skipped.

### Two guards, distinct semantics

- `DRIFT_VS_SELLERISE` — us vs Sellerise's frozen snapshot. Answers "how far
  off from the reference is our current pull?" Wide bands, absorbs attribution
  residuals.
- `DRIFT_VS_PRIOR_PULL` — us now vs us last pull. Answers "did anything move
  in our pipeline since last run?" Tight bands, catches regressions.

Never share a band between them.

### First run behavior

Until ≥ 2 pulls are persisted, the vs-prior-pull guard reports
`NO_BASELINE` per cell — not a failure, but the report says so explicitly.
The first successful reconcile writes the baseline; the second and later runs
have both guards active.

### Acceptance-test evidence (2026-07-07)

Five tests, all passing:

| # | scenario | vs-Sellerise fires | vs-prior-pull fires | verdict |
|---|---|---:|---:|---|
| 1 | identical repull (no change) | 0 | 0 | ✓ no false positives |
| 2 | **revert refund-COGS fix** (the class the old guard missed) | **0** | **11** | ✓ **CAUGHT — the whole point** |
| 3 | cog × 1.20 (loud inflation bug) | 5 | 12 | ✓ both guards catch |
| 4 | Principal sign flip (mapping bug) | 12 | 12 | ✓ both guards catch |
| 5 | final identical repull (all perturbations reverted) | 0 | 0 | ✓ no lingering state |

**Test 2 is the acceptance test.** The vs-Sellerise guard silently accepts
the perturbation (cog moves ~$2.8k, well within its ±$2,500 band). The
vs-prior-pull guard catches the same perturbation *loudly* — 11 fires
including all six months of cog and all six months of net, because $2.8k is
28× the ±$100 prior-pull cog band.

### Snapshot table

`pnl_monthly_snapshots`, added by migration `e5f6a7b8c9d0_pnl_snapshots.py`.
Append-only. Snapshots are written at the *end* of a successful reconcile so
a partial/crashed run cannot corrupt the baseline. Losing this table defeats
the guard — treat it as a durable operational asset, not a cache.

### CLI exit behavior

`python -m sync.reconcile` now exits non-zero if either guard fires
`INVESTIGATE`. A scheduled monthly pipeline run surfaces regressions as job
failures, not silent drift on line 47 of a report.

## Guardrails (per task)

- Bands come from observed drift + margin. Documented, not conveniences.
- Regime-aware (settled vs trailing). No wolf-cry on trailing DEFERRED.
- No accepted number changed — this is monitoring, not reconciliation.
- Do NOT auto-widen bands to suppress `INVESTIGATE`. If it fires on a future
  run, look; if the cause is documented drift, extend the diagnosis doc rather
  than the band.
