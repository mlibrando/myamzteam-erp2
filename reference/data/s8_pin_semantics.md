# S8 — making pinned defects survive live ingestion

Run 2026-07-10. Read-only against the data; no reported number moved; exit codes unchanged
(US 1 pre-existing, CA 0, UK 0, AU 0).

> ## Verdict
>
> **Rate-pinning does not work here, and the reason is structural.** I measured it before building it,
> and it fails on both UK families — it would either fire on the very refund it is meant to absorb, or
> need a tolerance so wide it stops being a pin. Details in § 2.
>
> **What does work is an ingestion horizon.** The target's file is *frozen*, so a pinned Δ moves only
> when **our** side moves — and there are exactly two ways our side moves: rows were ingested, or our
> code changed. `sp_transactions.ingested_at` and `order_purchase_date.ingested_at` tell those apart
> exactly. Recompute the cell using only rows ingested at or before the pin's `measured_at`. If the Δ
> is *still* pinned there, ingestion did all of it → **`DEFECT_REMEASURED`**. If the as-of Δ moved too,
> we did → **`INVESTIGATE`**.
>
> This handles **both** kinds of defect, needs no rate, widens no band, and cannot fire falsely: with
> nothing ingested past the horizon, the as-of Δ *is* the current Δ, so `DEFECT_REMEASURED` is
> unreachable. That is a structural guarantee, not a test result.

---

## 1. Classification — all 13 pinned cells

The test is *does the Δ scale with units, or is it a fixed set of items?*

| marketplace | cells | kind | evidence |
|---|---|---|---|
| UK | 4 × `cog.(scalar)` | **rate** | Sellerise derives per-SKU costs below the workbook's. Δ = Σ<sub>sku</sub> units × (workbook − Sellerise). Δ/net-unit varies 0.179–1.858 across the pinned months (**CV 55.5 %**) because the SKU mix moves. |
| UK | 5 × `fbaObject.FBAPerUnitFulfillmentFee` | **rate** | Sellerise books ~£0/unit for GMAKER-3 where Amazon bills £3.374/unit. Δ tracks GMAKER-3's unit share (10 % → 25 %) exactly. Δ/GMAKER-3-unit **CV 16.0 %**. |
| AU | 1 × `storageFee.storageFee` | **content** | Sellerboard omitted GST from **one line in one month**. A fixed £52.75, tied to that line, not to volume. |
| AU | 3 × `feesObject.Commission`, `fbaObject.FBAPerUnitFulfillmentFee`, `cog.(salesCosts)` | **content** | Sellerboard counted **exactly one** MCF unit (MBUKB1) in 2026-01. Fixed items: cog −86.71, commission +30.07, FBA +30.27. |

`kind` is recorded on every registry entry. Its real use is operational: a **rate** cell's Δ will drift
with next month's volume, so each new settled month needs its own entry; a **content** cell's Δ belongs
to specific items in one month and will not.

---

## 2. Why Step 2's rate-pinning does not survive measurement

The brief proposed pinning the *implied per-unit rate*, on the reasoning that "the dollar Δ moves, the
rate does not." Measured against the real data, it does move — for a reason that no normalisation can
remove.

### 2a. There is no month-independent rate to pin

`fbaObject`, per pinned month:

| month | Δ | ship units | Δ / ship unit | GMAKER-3 units | Δ / GMAKER-3 unit | Sellerise `FBAFees` | (Δ − FBAFees) / G |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-01 | −80.06 | 208 | −0.3849 | 21 | −3.8124 | −8.71 | −3.3976 |
| 2026-02 | −135.09 | 201 | −0.6721 | 35 | −3.8597 | −17.84 | −3.3500 |
| 2026-03 | −96.03 | 178 | −0.5395 | 26 | −3.6935 | −8.93 | −3.3500 |
| 2026-04 | −60.35 | 117 | −0.5158 | 24 | −2.5146 | 0.00 | **−2.5146** |
| 2026-05 | −64.30 | 72 | −0.8931 | 18 | −3.5722 | −3.10 | −3.4000 |
| | | | **CV 32.0 %** | | **CV 16.0 %** | | **CV 12.0 %** |

Even the best-behaved denominator leaves April as an outlier — it is the one month Sellerise booked
*anything* for GMAKER-3 (£20.70), so its per-unit understatement is genuinely different. Covering it
needs ±26 % on the rate, which is band-widening.

`cog` is worse: Δ/net-unit runs 0.179 → 1.858, **CV 55.5 %**. (The `ours/theirs` *ratio* looks stable at
CV 2.6 %, but its month-to-month range across the pinned months, 1.0461–1.0772, is the same size as the
perturbation below — so it has no teeth either.)

### 2b. Worse, a rate pin still fires on the case it exists to absorb

The observed event: a UK Refund posted 2026-07-04 on an order purchased 2026-01-18. UK's refund-COGS
basis is **purchase**, so it nets that unit out of **January's** cog.

Sellerise's snapshot is a **frozen file**. It does not shed the refunded unit's cost. So our side drops
by the full workbook cog and nothing offsets it:

| refunded SKU | workbook cog | Δ | Δ/unit | verdict under a tight rate pin |
|---|---:|---|---:|---|
| `4C-76GT-VAWZ` (observed) | £6.70 | 242.84 → 236.14 | 1.2986 → 1.2696 | passes |
| `ABDB` (adversarial) | £78.53 | 242.84 → **164.31** | 1.2986 → **0.8834** (**−32.0 %**) | **fires** |

A single refund of one expensive unit moves the *rate* by a third. Normalising by units cannot help,
because the numerator lost a high-cost unit's full cost while the denominator lost one unit. Nothing —
dollars, rate, or ratio — is invariant to a frozen target.

**That is the finding.** The Δ is not the wrong quantity to pin; the missing ingredient was never a
denominator, it was *knowing which rows the pin was taken over*.

---

## 3. The mechanism that does work

Two fields on `TargetDefect`:

- `kind` — `"rate"` or `"content"` (§ 1).
- `measured_at` — the **ingestion horizon**: every row with `ingested_at <= measured_at` is inside the
  pinned Δ.

and one status, `DEFECT_REMEASURED`. `classify()` becomes:

```python
if defect is not None:
    if defect.matches(delta):
        return KNOWN_TARGET_DEFECT
    if delta_as_of is not None and defect.matches(delta_as_of):
        return DEFECT_REMEASURED       # ingestion moved it; the defect is unchanged
    return "INVESTIGATE"               # we moved it, or the target changed
```

`delta_as_of` is the same cell recomputed with `ingested_before=defect.measured_at`. Both
`compute_pnl_in_memory` / `compute_cog_by_basis` (and AU's three loaders) take that horizon and add
`AND t.ingested_at <= %s` plus `AND opd.ingested_at <= %s` — no math changes, only which rows are
visible. The recompute is **lazy**: it runs only when a pin is actually off.

Why the guardrail holds *by construction*: with nothing ingested past the horizon, the horizoned query
returns exactly the current rows, so `delta_as_of == delta`. If `delta` fails to match the pin, so does
`delta_as_of`. **`DEFECT_REMEASURED` is unreachable on a run that ingested nothing.**

And the other cases fall out:

| what happened | current Δ | Δ at horizon | status |
|---|---|---|---|
| nothing | pinned | pinned | `KNOWN_TARGET_DEFECT` |
| new rows ingested | moved | **still pinned** | `DEFECT_REMEASURED` |
| our code changed | moved | **moved too** | `INVESTIGATE` |
| the target fixed its bug (Δ → 0) | moved | moved (the *target* changed, not our rows) | `INVESTIGATE` |
| an unregistered cell at the same Δ | — | — | `INVESTIGATE` (band) |

Exit code gates on `INVESTIGATE` alone. `DEFECT_REMEASURED` is loud — its own report section, the old
and new Δ, the Δ at the horizon, and the transactions that explain it, plus the exact registry lines to
paste — but it does **not** fail the run. An unattended job that goes red on a legitimate refund is
worse than no job.

---

## 4. The ingest protocol

Ingesting is a **deliberate act**, not a side effect.

1. **Phase 1 (ingest) and the guards are separate operations.** A verification or reporting run must
   not ingest. Hold `--start` past the `now − 48h` boundary so `sync_marketplace` returns immediately,
   and pass `--skip-orders`.
2. **Order: ingest → reconcile → guards.** In that order, once, deliberately.
3. **`DEFECT_REMEASURED` on the first guarded run after an ingest is expected.** On a run that ingested
   nothing it is impossible (§ 3), so if you ever see it there, it is a bug — not a stale pin.
4. **Re-pin promptly.** The report prints each entry's new `expected_delta`. Update `TARGET_DEFECTS`
   and set `measured_at` to a horizon after the ingest. Until you do, the cell keeps reading
   `DEFECT_REMEASURED` — correct, and loud, but stale.
5. **Never re-measure silently.** The Δ only changes in the source file, by hand, with the report's
   evidence in the commit message.

Every current entry carries `measured_at = 2026-07-10T00:00:00Z`. The latest `ingested_at` in
`sp_transactions` is `2026-07-07 07:38:39Z`, so that horizon sits after every existing row and before
any future one.

---

## 5. Verification

| check | result |
|---|---|
| **observed case** — UK Jan refund, `4C-76GT-VAWZ` (£6.70): Δ 242.84 → 236.14 | inside ±25 → `KNOWN_TARGET_DEFECT`, unmoved |
| **adversarial** — same refund but `ABDB` (£78.53): Δ 242.84 → 164.31 | old scheme: `INVESTIGATE`. **new scheme: `DEFECT_REMEASURED`** |
| **adversarial, under a rate pin** | rate 1.2986 → 0.8834 (−32.0 %) — would fire. Rate-pinning rejected |
| content Δ moved, ingestion does not explain it | `INVESTIGATE` |
| target fixes the defect (Δ → 0) | `INVESTIGATE` |
| our code moved it (current *and* as-of Δ moved) | `INVESTIGATE` |
| unregistered cell at the same Δ | `INVESTIGATE` — the pin widens nothing |
| `cog × 1.20`, `fbaObject × 1.20` perturbations | still fire on US / CA / UK |
| **`DEFECT_REMEASURED` on a no-ingest run** | unreachable for *any* Δ, by construction |
| horizon after every ingest is a no-op | `compute_pnl_in_memory` and `compute_cog_by_basis` return identical dicts |
| horizon mid-ingest really reconstructs the cell | UK Jan cog 3,388.38 → **3,608.71** when later-ingested refunds are excluded — the exact mechanism at issue |
| **live end-to-end**, `reconcile()` with a back-dated pin | `DEFECT_REMEASURED`, `remeasured_count=1`, `investigate_count=0`, report section rendered |
| same, with a pin no ingestion can explain | `INVESTIGATE`, `investigate_count=1` |
| registry restored | `KNOWN_TARGET_DEFECT`, 0 recomputes, `newly_ingested` never loaded (lazy) |
| **live end-to-end**, AU `_as_of_deltas()` with a back-dated pin | Δ −86.71 → +661.56 at the horizon → `DEFECT_REMEASURED` |
| all four reports | every numeric token identical to the pre-S8 baseline, in order |
| exit codes | US 1, CA 0, UK 0, AU 0 — unchanged |

## 6. Code changed

- `drift_bands.py` — `DEFECT_REMEASURED`; `TargetDefect.kind` + `.measured_at`; `classify(...,
  delta_as_of=None)`; all 13 entries classified and horizoned.
- `reconcile.py` — `ingested_before` on `compute_pnl_in_memory` / `compute_cog_by_basis`; a lazy as-of
  recompute for moved pins; `_load_newly_ingested`; the report section; counts and logging.
- `reconcile_au.py` — `ingested_before` on its three loaders; `_build_rows` / `_cell_deltas` /
  `_as_of_deltas`; `DEFECT_REMEASURED` in both its tables.
- `attribution.py` — `load_order_purchase_dates(..., ingested_before)`.

No reconciliation math, attribution policy, bucket map, band, schema, or `aggregate_marketplace`
return shape was touched. No band was widened.

## 7. What this does not cover

The horizon is on `sp_transactions.ingested_at` and `order_purchase_date.ingested_at`. **Ads
restatement is outside it**, because `ad_spend_daily` has no `ingested_at` — it has `as_of`, its own
audit trail, and its own drift bands.

For US/CA/UK this is moot: no pinned cell reads ad spend. **For AU it is a real, if narrow, gap.**
AU's FX reference rate is set from the refund *and advertising* anchors (`reconcile_au.reference_rate`),
and every AU pinned Δ is `theirs − ours × rate`. So a large ads restatement moves the rate, moves the Δ,
and — since the horizon cannot exclude it — reads `INVESTIGATE` rather than `DEFECT_REMEASURED`. That is
the safe direction (it alarms rather than absolves), and the measured ads restatement is −$8.82 over
three days against AU tolerances of ±17.00–21.65. But it is a margin, not a proof. If it ever bites, the
fix is to give `ad_spend_daily` an `ingested_at` alongside `as_of` and horizon it too.
