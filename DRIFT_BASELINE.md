# Claude Code Task — Establish the restatement-drift baseline (make the live pipeline trustworthy)

## Context

US reconciliation is complete and accepted: cumulative net Δ is +$3,568 (+1.7% of Sellerise
net), every dollar traced to a named cause (pre-backfill boundary, revenue-side snapshot
restatement drift, trailing-month refund lag), with no unexplained bucket. See
`reference/data/net_residual_diagnosis.md`.

That close-out reconciled against a **single Sellerise snapshot frozen at one point in time**.
The diagnosis proved — three times — that both Amazon's data and Sellerise's snapshot move after
the fact (ads `PASS_DRIFT`, Mar/Apr revenue, Jun refunds). This creates an unclosed operational
gap: **when the live pipeline re-pulls next month, there is currently no principled way to tell
restatement drift (expected) from a pipeline regression (a bug).** A settled month that
reconciled to +$743 could read +$900 next pull and look identical whether Amazon restated it or
our code broke.

This task does **not** re-open the residual. It establishes the drift baseline and a guardrail so
the monthly pipeline is trustworthy. It is verification + a small monitoring addition, not a
reconciliation change.

## Operating rules

- Do not change net math, mappings, COGS, or attribution — those are locked and accepted.
- Verify with real numbers; the deliverable is a baseline + a check, not a new computation of net.
- Minimalist: reuse existing pull/reconcile code and the `as_of` timestamps already persisted.

## Step 1 — Characterize the drift you already have

- Correct the close-out framing first: total the **revenue-side snapshot restatement drift**
  across *all* settled months (Jan/Feb portion identified in Check 2 as ~$2,159 + Mar/Apr's
  ~$1,431), so the largest residual category is stated as one number, not split. Confirm it
  against the per-month decompositions already in the diagnosis doc.
- Using the `as_of` timestamps on `ad_spend_daily` (and any other re-pulled data), quantify the
  **observed** drift magnitude per month per bucket from the pulls you already have on record —
  i.e. how much did a given month's numbers actually move between pulls. This is your empirical
  drift distribution, not a guess.

## Step 2 — Set per-bucket drift bands from the data

- From Step 1, derive a per-bucket expected-drift band for a **settled** month (e.g. revenue
  ±X%, cog ±Y, refunds ±Z, ads the sub-dollar/few-dollar band already established). Base the
  bands on observed drift plus a margin, not on round numbers.
- Distinguish two regimes explicitly: **trailing month** (still moving a lot — Jun-style refund
  lag) vs **settled month** (should only move within the small restatement band). The bands
  differ by regime; a settled month drifting beyond its band is the signal that matters.

## Step 3 — Add the regression guard to the monthly reconcile

- On each monthly run, for every settled month, compare the new per-bucket delta-vs-Sellerise (or
  delta-vs-prior-pull) against its band from Step 2. Emit one of three statuses per bucket:
  `WITHIN_DRIFT` (expected restatement), `TRAILING` (current month, expected to move), or
  `INVESTIGATE` (moved beyond the settled-month band — possible regression).
- `INVESTIGATE` is the whole point: it's what separates "Amazon restated" from "our pipeline
  changed." A settled month should essentially never fire `INVESTIGATE` unless something in our
  code or the mapping changed. Make it loud (report line + log), not silent.
- Do not auto-widen bands to suppress `INVESTIGATE`. A firing guard is a signal to look, not a
  threshold to relax.

## Step 4 — Verify the guard on known-good data

- Run the guard against the current accepted state: every settled month must come back
  `WITHIN_DRIFT` (they're all accepted, so none should fire `INVESTIGATE`). If one fires, either
  the band is too tight or a real issue is present — resolve before shipping the guard.
- Sanity-check it can *catch* a regression: temporarily perturb one bucket (e.g. re-introduce the
  pre-fix cog-not-netting-refunds behavior) and confirm the affected months fire `INVESTIGATE`.
  Revert the perturbation. This proves the guard has teeth.

## Guardrails

- This is monitoring, not reconciliation — do not alter any accepted number or label.
- Bands come from observed drift, not convenience; document how each was derived.
- The guard must be regime-aware (trailing vs settled) or it will cry wolf on every current month.

## Definition of done

- Revenue-side restatement drift stated as one cross-month total; drift distribution quantified
  from actual `as_of` pull history.
- Per-bucket, per-regime drift bands derived from data and documented.
- Monthly reconcile emits `WITHIN_DRIFT` / `TRAILING` / `INVESTIGATE` per settled bucket.
- Guard verified: all current settled months read `WITHIN_DRIFT`; a deliberately perturbed bucket
  correctly fires `INVESTIGATE`, then reverted.
- Written up in `reference/data/drift_baseline.md` — no accepted reconciliation number changed.