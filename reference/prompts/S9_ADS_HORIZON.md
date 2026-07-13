# Claude Code Task — S9: extend the ingestion horizon to ad_spend_daily (AU)

## Context

S8 landed: pinned defects are classified by recomputing the cell at the pin's **ingestion horizon**.
If the as-of Δ still matches the pin, new rows explain the movement → `DEFECT_REMEASURED`. If the as-of
Δ moved too, our code changed → `INVESTIGATE`. The guardrail holds by construction.

**The horizon covers `sp_transactions` and `order_purchase_date`. It does not cover `ad_spend_daily`.**

Moot for US/CA/UK. **Real for AU**: its FX reference rate is anchored on **refunds and advertising**, so
an Amazon ads restatement moves an AU pinned Δ and reads `INVESTIGATE` rather than `DEFECT_REMEASURED`.
That errs toward alarming rather than absolving — safe, but it is exactly the false positive S8 exists
to prevent, and the cron will run unattended.

Measured, not assumed: Amazon restated June ads by **−$8.82 across 8 rows over three days** (US −$8.34,
UK −£0.48), all revised downward; Jan–May moved by zero. AU's tolerances are ±17.00–21.65, so today's
restatement sits inside them. **That is a margin, not a proof** — three days is not the restatement
window, and Amazon has been observed revising over weeks.

## Operating rules

- **Simplicity.** Extend the existing as-of recompute to one more table. No new abstraction, no schema
  redesign, no refactor of `classify()`.
- Change no reconciliation math, attribution, bucket maps, bands, or reported numbers.
- Measure before building: the first question is whether `as_of` can serve as a horizon at all.

## Step 1 — Determine whether `as_of` is usable as a horizon (gate)

`ad_spend_daily` has `as_of`, not `ingested_at`. These are not the same thing:

- If `as_of` is a **pull timestamp** (when we fetched the row), it is a horizon — filter
  `as_of <= measured_at` and the recompute works exactly like `ingested_at`.
- If `as_of` is a **data-vintage stamp** (Amazon's notion of when the data was current), it is **not** a
  horizon: a restated row may carry a new `as_of` while replacing an old row at the same PK, so
  filtering on it cannot reconstruct the pre-restatement state.

Determine which it is by reading how `ads_spend.py` sets it and how `_replace_month` interacts with it.
**Report the answer with evidence before writing code.**

- If it is a pull timestamp → Step 2a.
- If it is not → Step 2b.

## Step 2a — `as_of` works as a horizon

- Extend the as-of recompute to filter `ad_spend_daily` on `as_of <= measured_at`, alongside the existing
  `ingested_at` filters. AU only needs it, but apply it uniformly if that is simpler than special-casing.
- That is the whole change.

## Step 2b — `as_of` is not a horizon

- The problem: `_replace_month` deletes and reinserts, so the pre-restatement row is gone. You cannot
  reconstruct it from the current table at any horizon.
- **Minimal fix, not a redesign:** keep the prior values. Either add `ingested_at` and stop replacing
  rows in place, or (simpler) record the replaced rows to a small append-only history table before
  `_replace_month` deletes them. Pick the smaller change and say why.
- Do **not** build a general versioning system. One month's prior ad rows per marketplace is enough to
  answer "what was this cell's Δ at the horizon."

## Step 3 — Verify against the real restatement, not a synthetic one

- Use the **measured** June restatement (8 rows, −$8.82, US −$8.34 / UK −£0.48) as the test case. It is
  already in the Step-0 backups from the blockers task, so a before/after pair exists.
- Construct the case that matters: an AU pinned cell whose Δ moves **because ads restated**. Under the
  fix it must read `DEFECT_REMEASURED`, not `INVESTIGATE`.
- **Adversarial, since today's restatement is small:** scale a restatement large enough to exceed AU's
  ±17.00–21.65 tolerance and confirm it still reads `DEFECT_REMEASURED` (the ads rows explain it), while
  a code change that moves both current and as-of Δ still reads `INVESTIGATE`. A small restatement
  passing inside tolerance proves nothing.
- Teeth intact: content Δ moving with no explaining rows → `INVESTIGATE`; target fixes its bug (Δ→0) →
  `INVESTIGATE`; unregistered cell at the same Δ → fires; `cog × 1.20` / `fbaObject × 1.20` → fire.
- `DEFECT_REMEASURED` still unreachable on a no-ingest run (the S8 construction must survive).

## Guardrails

- No band widened. No tolerance loosened to make the restatement fit.
- Do not run Phase 1 during verification (hold `--start` past the 48h boundary).
- Back up `ad_spend_daily` before any write that touches it.
- No reported number may move; exit codes unchanged (US 1 pre-existing, CA/UK/AU 0).
- If `as_of` turns out not to be a horizon and the minimal fix is larger than it looks, **stop and
  report** rather than building a versioning layer.

## Definition of done

- Stated with evidence whether `as_of` is a pull timestamp or a data-vintage stamp.
- Horizon extended to `ad_spend_daily` (2a) or prior ad rows preserved minimally (2b), with the choice
  justified.
- Verified against the **real** June restatement, plus a scaled-up adversarial restatement that exceeds
  AU's tolerance and still reads `DEFECT_REMEASURED`.
- All S8 teeth tests still pass; `DEFECT_REMEASURED` still impossible on a no-ingest run.
- No number moves, no band widened, no schema redesign.