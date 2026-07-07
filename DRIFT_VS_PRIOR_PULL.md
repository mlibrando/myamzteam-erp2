# Claude Code Task — Add the vs-prior-pull drift guard (catch the regression the current guard can't)

## Context

The drift baseline + vs-Sellerise guard is built and verified
(`reference/data/drift_baseline.md`). Its verification was honest and surfaced the critical gap:
of three perturbations, it caught the two *loud* classes (20% cog inflation, Principal sign flip)
but **missed reverting the refund-COGS fix** — the exact systematic bug this project spent three
diagnosis cycles finding.

That miss is structural, not a tuning issue: the cog band must be ~±$2,500 to absorb Jan's $2,019
pre-backfill boundary, which is necessarily wide enough to hide a ~$2,800 systematic shift that
partially offsets that same boundary. **The guard reliably catches loud bugs you'd likely notice
anyway, and misses the quiet systematic class that's hardest to find by hand.** That's inverted
from what a monitor should do, and it's the whole reason to do this task now.

The fix is already named in the baseline doc: a **vs-prior-pull** guard. It's blocked only on
there being no `pnl_monthly` snapshot history to compare against. This task unblocks it.

## Why this is time-sensitive (do it now, not later)

The vs-Sellerise guard works from day one. The vs-prior-pull guard only becomes possible after
**two** pulls are persisted — so it can't catch anything until snapshot history exists. **Every
monthly run without snapshot persistence is a month of baseline that can never be recovered.**
Turning on snapshotting starts the clock; delaying it delays the start of the clock, not just the
feature.

## Operating rules

- Do not change net math, mappings, COGS, attribution, or any accepted number — this is
  monitoring only.
- Minimalist: one snapshot table + one guard function + report wiring. No new dependencies.
- Verify with real numbers; the deliverable's proof is catching the bug the current guard misses.

## Step 1 — Persist `pnl_monthly` snapshots per pull

- On each reconcile run, snapshot the full per-(month, bucket, sub_line) `pnl_monthly` output to a
  history table keyed by `(pull_timestamp, ym, bucket, sub_line)` with the value and the same
  `as_of` provenance used elsewhere.
- Idempotent per pull; never overwrite a prior pull's snapshot (that history is the entire point).
- This begins accumulating immediately — even before the second guard can act, so the clock starts
  on this run.

## Step 2 — Add the vs-prior-pull guard with its OWN (tight) bands

- New guard: for each settled cell, compare **current value vs the most recent prior pull's
  snapshot** of the same cell. This measures pure pull-to-pull movement — no attribution residual,
  no Sellerise-snapshot offset.
- **Its bands must be much tighter than the vs-Sellerise bands.** Anchor them to *observed
  pull-to-pull drift*, not to the vs-Sellerise deltas. The baseline already found ads moved $0.00
  over ~13h; restatement accumulates on week-to-month scales, so a settled cell's month-over-month
  pure drift is small. Do NOT reuse the ±$1,500 / ±$2,500 vs-Sellerise bands here — that would
  recreate the exact blind spot. Derive vs-prior-pull bands from what cells actually move between
  pulls (start conservative, tighten as snapshot history grows).
- Keep the two guards distinct and clearly labeled: `DRIFT_VS_SELLERISE` (us vs their frozen
  snapshot) and `DRIFT_VS_PRIOR_PULL` (us now vs us last pull). They answer different questions;
  never share a band.
- Regime-aware, same as the existing guard: trailing month expected to move; DEFERRED `EXPECTED`
  lines skipped.

## Step 3 — Report + exit code

- Add a `DRIFT_VS_PRIOR_PULL` section mirroring the existing one: `WITHIN_DRIFT` / `TRAILING` /
  `INVESTIGATE`, with `INVESTIGATE` sorted first and a WARNING log.
- The CLI exits non-zero on either guard's `INVESTIGATE`. Until ≥2 pulls exist, the vs-prior-pull
  guard reports `NO_BASELINE` (not a failure) and says so explicitly.

## Step 4 — Verify it catches the bug the current guard misses (the acceptance test)

- Simulate two pulls: pull 1 = current locked/correct state (snapshot it); pull 2 = **revert the
  refund-COGS fix**, re-run.
- The vs-prior-pull guard **must fire `INVESTIGATE`** on the cog cells in pull 2 — because
  cog moved ~$2.8k *from the prior pull* even though its |Δ vs Sellerise| stayed within band. This
  is the exact regression the vs-Sellerise guard could not catch; proving this guard catches it is
  the whole point of the task. Revert the perturbation.
- Also confirm no false positive: two identical consecutive pulls of the correct state must read
  all `WITHIN_DRIFT` (or `NO_BASELINE` on the first), zero `INVESTIGATE`.
- Re-run the loud perturbations (cog ×1.20, Principal sign flip) and confirm both guards still fire
  — the new guard must not regress the old coverage.

## Guardrails

- Two guards, two band sets — never conflate. The vs-prior-pull bands are tight by design.
- Do not auto-widen either band to suppress `INVESTIGATE`; a fire is a signal to look. If the cause
  is documented drift, extend the diagnosis doc, not the band.
- Snapshot history is append-only; losing it defeats the guard.

## Definition of done

- `pnl_monthly` snapshots persisted per pull (append-only, pull-timestamped), accumulating from
  this run onward.
- `DRIFT_VS_PRIOR_PULL` guard added with its own tight, observed-drift-derived bands, distinct from
  the vs-Sellerise guard; report section + non-zero exit wired; `NO_BASELINE` until ≥2 pulls.
- Acceptance test passed: **reverting the refund-COGS fix fires `INVESTIGATE` on the vs-prior-pull
  guard** (the case the current guard misses), identical pulls produce zero false positives, and the
  loud perturbations still fire on both guards.
- Written up in `drift_baseline.md` — the "known limitation" section replaced with the implemented
  second guard and its verification. No accepted reconciliation number changed.