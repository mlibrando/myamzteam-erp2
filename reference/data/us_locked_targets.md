# US's permanent exit 1 — resolved (locked targets 9/15 → 9 PASS · 6 ACCEPTED_DRIFT · 0 FAIL)

Run 2026-07-10. Read-only against the data; no financial number moved; CA/UK/AU reports byte-identical;
US now exits **0**.

> ## Verdict
>
> The "9/15" was the **pass** count — there were **6** failures, not 9 (the prompt's "9 failing" is a
> slip). All 6 are decision-D/E `Promotion`/`RestockingFee` cells, and every one is **accepted
> restatement drift the drift guard already accepts** on that cell's own band. None is stale-predating-a-
> fix (the golden figures still equal Sellerise), and none is a bug (our values correctly sum the current
> Amazon leaves). The locked-target check was asserting **exact** equality to a **frozen** golden figure
> on cells that legitimately drift — which fails permanently for a non-regression, the exact "red every
> run → ignored" trap.
>
> **Fix:** a locked target that misses its exact figure but stays within that cell's drift band is
> `ACCEPTED_DRIFT` (restatement, not a regression; does not fail the run); outside the band it is `FAIL`
> (a real regression; still exits 1). The gate now means what the drift gate means. **Updating the 6 to
> "current" was rejected** — the current value drifts too, so it would just reset the clock and
> reintroduce the periodic red this task exists to kill.

---

## Step 1 — what "locked targets" is

`US_LOCKED_TARGETS` (`reconcile.py:73-89`) is 15 golden figures `(bucket, sub_line, month, expected,
decision)` from RECONCILIATION.md Step 3 — values our pipeline reproduced at lock time, when it also
equalled Sellerise. Evaluated at `reconcile.py:840`: `actual = pnl_after[month][bucket][sub_line]`,
`delta = actual − expected`, and (before this task) `PASS` iff `|delta| < $0.01`, else `FAIL`. The exit
gate required every locked target to PASS.

This is a **third** construct, distinct from the two guards:

| | asserts | tolerance |
|---|---|---|
| **drift guard** | our value vs the **live** Sellerise file | per-cell restatement band |
| **`KNOWN_TARGET_DEFECT`** | a diagnosed our-vs-target Δ, pinned | tight, per defect |
| **locked target** | our value vs a **hardcoded golden figure** | exact, ±$0.01 |

Only US has locked targets; CA/UK/AU lists are `[]`.

## The 15, and the 6 failures

| # | cell | month | dec | expected | actual | Δ | (old) status |
|---|---|---|---|---:|---:|---:|---|
| 1–4 | `feesObject.ReferralFee` / `fbaObject.FBAFees` | Feb, Mar | A | 0.00 | 0.00 | 0.00 | PASS |
| 5 | `refundsObject.RestockingFee` | 2026-02 | D | 52.94 | 52.94 | 0.00 | PASS |
| **6** | `refundsObject.RestockingFee` | 2026-04 | D | 4.59 | 4.87 | **+0.28** | **FAIL** |
| 7 | `refundsObject.RestockingFee` | 2026-06 | D | 9.70 | 9.70 | 0.00 | PASS |
| 8–9 | `refundsObject.Goodwill` | May, Jun | D | −17.09 / −13.23 | = | 0.00 | PASS |
| 10 | `refundsObject.Promotion` | 2026-02 | E | 146.99 | 146.99 | 0.00 | PASS |
| **11** | `refundsObject.Promotion` | 2026-03 | E | 44.87 | 46.87 | **+2.00** | **FAIL** |
| **12** | `refundsObject.Promotion` | 2026-06 | E | 3.99 | 4.99 | **+1.00** | **FAIL** |
| **13** | `chargesObject.Promotion` | 2026-02 | E | −811.14 | −819.10 | **−7.96** | **FAIL** |
| **14** | `chargesObject.Promotion` | 2026-03 | E | −610.03 | −613.51 | **−3.48** | **FAIL** |
| **15** | `chargesObject.Promotion` | 2026-06 | E | −496.12 | −505.04 | **−8.92** | **FAIL** |

## Step 2 — classification (all 6: accepted restatement drift)

Three pieces of evidence, per cell:

**(a) Our value correctly sums the current Amazon leaves.** `Promotion` = `OurPriceDiscount +
ShippingDiscount` on the relevant side, summed exactly. e.g. Feb `chargesObject.Promotion` −819.10 =
Shipment `OurPriceDiscount` −176.15 + `ShippingDiscount` −642.95. No mapping or attribution bug — Feb
`refundsObject.Promotion` still matches its golden figure to the cent (146.99), using the *same*
mapping as the months that drifted.

**(b) The golden figure still equals Sellerise** (5 of 6; Jun `chargesObject.Promotion` even Sellerise
moved, −496.12 → −499.51). So the lock is a frozen Sellerise snapshot, and our value differs from it by
restatement — Amazon revised these leaves after Sellerise snapshotted them.

**(c) The Δ is within the cell's drift band — the guard already accepts it:**

| cell | month | Δ vs Sellerise | band | drift status |
|---|---|---:|---:|---|
| `refundsObject.RestockingFee` | 2026-04 | +0.28 | 5 | WITHIN_DRIFT |
| `refundsObject.Promotion` | 2026-03 | +2.00 | 20 | WITHIN_DRIFT |
| `refundsObject.Promotion` | 2026-06 | +1.00 | 60 (trailing) | TRAILING |
| `chargesObject.Promotion` | 2026-02 | −7.96 | 60 | WITHIN_DRIFT |
| `chargesObject.Promotion` | 2026-03 | −3.48 | 60 | WITHIN_DRIFT |
| `chargesObject.Promotion` | 2026-06 | −5.53 | 180 (trailing) | TRAILING |

The `chargesObject.Promotion` band is literally `Decimal("60")  # decision-E residual` — the band
machinery was sized for exactly this residual. So the drift guard (US: **0 INVESTIGATE**) already
accepts all six; the locked-target exact-match was a redundant, stricter, restatement-incompatible
check on the same cells.

**None is stale-predating-a-fix:** no fix moved these — data restatement did, and the golden figures
still track Sellerise. **None is a genuine unresolved residual:** each is a correct sum within an
accepted band. → all 6 are **accepted restatement drift**.

## Step 3 — action

Not "update to current" (the task's stale path): the current value **also** drifts, so re-pinning it
resets the clock and reintroduces periodic red — the failure this task exists to prevent. The guardrail
agrees: *"a stale target is only stale if the number that replaced it is right"*, and here no stable
right number exists.

Instead, give the locked-target check the restatement-awareness the rest of the project already uses.
`reconcile.py` locked eval:

```python
if abs(delta) < TOLERANCE:      status = "PASS"            # exact
elif abs(delta) < band:         status = "ACCEPTED_DRIFT"  # within the cell's drift band
else:                           status = "FAIL"            # a real regression
```

`band` is `drift_bands.band_for(bucket, sub_line, is_trailing, marketplace_id)` — **read, never
altered.** The exit gate moves from "all PASS" to "no FAIL":

```python
all_good = locked_fail == 0 and inv_s == 0 and inv_p == 0
```

The structural decision-A zeros (0.00, don't drift) still require exact PASS.

## Step 4 — verification

| check | result |
|---|---|
| US exit code | **1 → 0** |
| US locked targets | 9 PASS · **6 ACCEPTED_DRIFT** · **0 FAIL** of 15 |
| **teeth** — a golden figure corrupted beyond its band | `FAIL`, US exits **1** |
| **teeth** — Δ just inside band (−59 vs band 60) | `ACCEPTED_DRIFT` |
| **teeth** — the decision-A structural zeros | still exact `PASS` |
| CA / UK / AU reports | **byte-identical** |
| US report outside the locked section | **byte-identical** |
| US locked table expected/actual/delta | **identical** (only status labels + summary changed) |
| CA / UK / AU exit codes | 0 / 0 / 0, unchanged |
| S8/S9 suites (KTD, FBA pin, pin semantics, ads horizon) | all pass |
| drift bands / `TARGET_DEFECTS` | unchanged (13 entries; bands read-only) |

The exit code now means the same thing on all four marketplaces: **red iff a real regression or an
unexplained residual.** US's Promotion/RestockingFee restatement is drift, named and bounded, not noise.

## Code changed

`reconcile.py` only: the locked-target status now has three values (`PASS` / `ACCEPTED_DRIFT` / `FAIL`,
graded on the cell's existing drift band); the exit gate keys on `FAIL`; the report annotates the band
on drift/fail rows and appends the breakdown to the summary. No reconciliation math, attribution, bucket
map, band, tolerance, `KNOWN_TARGET_DEFECT` entry, or golden figure was touched. The report changes are
confined to the US locked-targets section; empty-list marketplaces render exactly as before.

## Note

The locked-target mechanism is now semantically a subset of the drift guard for the drift-prone cells
(same band, same accept/fail line) — with one distinct value: its `expected` is a **hardcoded** golden
figure, so it would still catch a corrupted Sellerise file that the live-file drift guard would miss.
That is a small, real reason to keep it rather than delete it. If a future cleanup does remove the
decision-D/E locked targets as redundant, the decision-A structural zeros should stay — they assert a
property (no DEFERRED estimate in a settled month) that does not drift and is worth a hard check.
