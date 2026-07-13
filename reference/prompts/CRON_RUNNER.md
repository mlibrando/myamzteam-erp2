# Claude Code Task — Thin cron runner: ingest → reconcile → guards, exit-code alerting, log only

## Context

Everything is committed on `main` and all four marketplaces exit 0 meaning the same thing (red = a
human should look). The last build is a **cron entrypoint**: one script that runs the monthly pipeline
for all four marketplaces in order, maps guard statuses to an exit code, and logs the outcome. **No
notification integration yet** — Railway scheduling later reads the exit code, so getting the exit-code
contract right now makes Railway alerting a config step, not new code.

## The exit-code contract (this is the whole design)

Per marketplace, after ingest → reconcile → guards:

| status | job outcome |
|---|---|
| `INVESTIGATE` (or a crash) | **fail** — exit non-zero. "Go look." |
| `DEFECT_REMEASURED` | **succeed** — exit zero, but log prominently. Expected on the first run after an ingest. |
| `ACCEPTED_DRIFT` / `KNOWN_TARGET_DEFECT` / `WITHIN_DRIFT` / `TRAILING` | silent, exit zero. |

The runner exits non-zero **iff** any marketplace hit `INVESTIGATE` or crashed. `DEFECT_REMEASURED` must
**not** fail the run — otherwise the first scheduled run after every monthly ingest goes red on a
legitimate event, the exact cry-wolf trap S8 exists to prevent.

## Operating rules

- **Simplicity.** One runner script + the exit-code mapping. No notification library, no email/Slack, no
  digest formatter, no Railway code. Log to stdout (Railway captures it); optionally one durable
  run-record row if trivial with the existing DB.
- Reuse the existing ingest / reconcile / guard entrypoints. Do not reimplement them.
- Change no reconciliation math, attribution, bands, tolerances, or the guard classification.

## Step 1 — The runner

- A single entrypoint (e.g. `python -m sync.cron` or a small `run_pipeline` script) that, for each of
  US / CA / UK / AU in turn:
  1. runs the pipeline in the §10 order: **ingest → reconcile → guards**;
  2. captures that marketplace's result: exit status + the guard status counts + any `INVESTIGATE` cells.
- **One marketplace failing must not skip the others.** Wrap each marketplace so a crash is caught,
  logged, and counted as a failure for that marketplace — then continue to the next. The run reports on
  all four regardless.

## Step 2 — Ingest-awareness (so the log is trustworthy)

- The runner knows whether it actually ingested (Phase 1 pulled new rows) vs ran no-op.
- `DEFECT_REMEASURED` is **legitimate only on a run that ingested**. Log accordingly:
  - post-ingest run + `DEFECT_REMEASURED` → "expected: N cells remeasured after ingest" (not a failure).
  - no-ingest run + `DEFECT_REMEASURED` → this is a bug per S8's construction; log it as an anomaly
    (still don't crash the cron, but make the log say clearly that this should be impossible).
- This is a few lines, but it's the difference between a log you trust and one you learn to ignore.

## Step 3 — The log line

For each run, emit a legible summary to stdout:
- per marketplace: exit status, and counts of `INVESTIGATE` / `DEFECT_REMEASURED` / `ACCEPTED_DRIFT` /
  `KNOWN_TARGET_DEFECT` / `WITHIN_DRIFT` / `TRAILING`;
- for any `INVESTIGATE`: the specific cells (marketplace, month, bucket, sub_line, Δ) — this is what a
  human needs to start looking, so don't make them re-run anything to get it;
- a final line: overall result (`OK` / `INVESTIGATE` / `CRASH`) and the exit code.

Keep it plain text, greppable. No formatting framework.

## Step 4 — Exit code

- Exit **0** if every marketplace is `OK` or only `DEFECT_REMEASURED` / drift / known-defect.
- Exit **non-zero** if any marketplace has `INVESTIGATE` or crashed.
- Distinct codes are fine if trivial (e.g. 1 = INVESTIGATE, 2 = crash), but not required — non-zero is
  the contract Railway will read.

## Step 5 — Verify unattended-safety

- Run it end to end today (no-ingest, since we hold `--start` past the 48h boundary in verification):
  all four should come back drift/known-defect/OK, exit 0, and the log shows no `DEFECT_REMEASURED`
  (correct on a no-ingest run).
- Simulate one marketplace crashing (e.g. a bad marketplace arg): the runner must log it, mark that
  marketplace failed, still process the others, and exit non-zero.
- Simulate an `INVESTIGATE` (reuse an existing perturbation): exit non-zero, the offending cells named
  in the log.
- Confirm the normal all-clear path exits 0. No reported number moves; the four reconcile reports are
  unchanged by the runner (it orchestrates, it doesn't recompute).

## Guardrails

- No notification code, no external service, no Railway config — exit code + stdout only.
- `DEFECT_REMEASURED` never fails the run. Verify this explicitly.
- One marketplace's failure never silently drops the others.
- Reuse existing entrypoints; change no math, bands, or guard logic.

## Definition of done

- A single cron runner runs ingest → reconcile → guards for all four marketplaces, isolating per-market
  failures.
- Exit code follows the contract: non-zero only on `INVESTIGATE` or crash; `DEFECT_REMEASURED` and drift
  exit 0.
- Log is plain-text, greppable, names any `INVESTIGATE` cells, and distinguishes post-ingest vs no-ingest
  `DEFECT_REMEASURED`.
- Verified: all-clear → 0; crash in one market → other three still run, exit non-zero; INVESTIGATE →
  exit non-zero with cells named.
- No notification/Railway code. No reported number changed.

## Note for the Railway phase (not built here)

Railway scheduling will point a scheduled job at this runner. Because the runner exits non-zero on
`INVESTIGATE`/crash, Railway's native failed-job alerting is the notifier — no notification code needed
in the app. The only later decision is the channel (Railway email / a webhook to Slack), made at deploy
time. Record this in the runner's module docstring so the intent is on file.