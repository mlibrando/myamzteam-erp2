# Claude Code Task — Commit cron.py + close the snapshot-integrity question before scheduling

## Context

`backend/sync/cron.py` is built and verified (exit 0 = OK/drift/known-defect/DEFECT_REMEASURED,
1 = INVESTIGATE, 2 = crash-dominates; guard code untouched). It's staged, ready to commit.

Building it surfaced a real hazard: **`reconcile()` commits a `pnl_monthly_snapshots` row on every
call, so the runner is not read-only — every run advances the vs-prior-pull baseline.** The
perturbation test poisoned that baseline (a cog×1.5 snapshot got committed, making the next run fire a
spurious prior-pull INVESTIGATE); it was found, deleted, and the test made self-cleaning.

That's the S8/S9 "running the thing changes the thing" hazard, one layer out. Two consequences to close
**before** Railway schedules anything that writes to that table unattended.

## Operating rules

- **Simplicity.** Commit the file; run two checks; fix only what the checks turn up. No refactor of the
  snapshot mechanism, no new abstraction.
- Change no guard code, reconciliation math, bands, or reported numbers.
- If a check turns up something non-trivial, **stop and report** rather than expanding scope.

## Step 1 — Commit cron.py, with the gotcha documented where it's dangerous

- Commit `cron.py`. The commit message must record the snapshot-baseline hazard prominently:
  `reconcile()` writes a `pnl_monthly_snapshots` row per call; any test driving the real `reconcile()`
  contaminates the vs-prior-pull baseline; perturbation tests must self-clean.
- Add a short comment in `cron.py` right where it calls `reconcile()` noting that the call advances the
  prior-pull baseline (so a future reader knows the runner is not read-only).
- Do not push unless asked.

## Step 2 — Sweep pnl_monthly_snapshots for other poisoned rows

The perturbation-test poisoning proves the class of bug exists. Earlier perturbation testing in this
project may have left other perturbed snapshots behind (S8 deliberately tested at the classify layer to
avoid this, but not every test did).

- Inspect `pnl_monthly_snapshots` for rows whose values are inconsistent with the known-good reconciled
  figures — e.g. a cog that's ~1.2×/1.5× a neighbor (perturbation multipliers used in tests), or a
  snapshot whose value doesn't match the committed reports for that (marketplace, month, cell).
- Report any suspects with evidence (which run/timestamp, expected vs stored). **Do not bulk-delete** —
  list them, and delete only rows clearly identifiable as test poison (matching a known perturbation
  factor and out of line with the golden reports). If any are ambiguous, report and leave them.
- Confirm the baseline each marketplace would read on the next run matches the golden reconciled values
  (e.g. US cog baseline back to the normal figure, as the cron fix already restored).

## Step 3 — Confirm the crash path doesn't leave a partial baseline

- Trace what `pnl_monthly_snapshots` contains for a marketplace whose reconcile **crashes mid-run**
  (the exit-2 path). Does the snapshot row get written before or after the point that can crash?
- If a crash can leave a partial or missing snapshot the next run would misread as a baseline, that's a
  real problem — report it with the mechanism. The minimal fix is to only write the snapshot on a
  *completed* reconcile (mirror the `_replace_month`-on-COMPLETED pattern already used for ad rows), but
  **only implement if the trace shows a real partial-write window** — don't add transactionality
  speculatively.
- If the snapshot is already all-or-nothing (written only on success), confirm that and move on.

## Step 4 — Record the deployment landmine

- One line in the cron module docstring (and § in the audit): **test runs must never touch the
  production `pnl_monthly_snapshots` table** — Railway must run the scheduled job against the prod DB,
  but any perturbation/CI testing must use a separate DB or be self-cleaning, or it corrupts the
  prior-pull baseline the next production run trusts.
- This is documentation, not code — it's the config decision the deploy phase must not miss.

## Guardrails

- Do not bulk-delete snapshot rows; identify test poison specifically, report ambiguous ones.
- Do not add snapshot transactionality unless Step 3 shows a real partial-write window.
- No guard code, math, bands, or reported numbers changed.
- `pnl_monthly_snapshots` is append-only in normal operation — only remove rows proven to be test poison.

## Definition of done

- `cron.py` committed, with the snapshot-baseline hazard in the commit message and a comment at the
  `reconcile()` call site. Not pushed.
- `pnl_monthly_snapshots` swept: any test-poison rows listed with evidence and removed only if
  unambiguous; each marketplace's next-run baseline confirmed to match the golden reconciled values.
- Crash path traced: snapshot confirmed all-or-nothing, or the partial-write window reported (and fixed
  only if real).
- Deployment landmine (test DB vs prod DB / snapshot table) recorded in the docstring and audit.
- No guard/math/band/number changes.