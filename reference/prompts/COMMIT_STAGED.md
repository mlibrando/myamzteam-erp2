# Claude Code Task — Commit the staged work in sensible boundaries

## Context

Everything is staged. Reconciliation, guards, S8/S9, and the locked-targets fix are all done and
verified; all four marketplaces exit 0 (US now 0 after the locked-target grading change). The tree just
needs committing before the cron work begins — a scheduler must run against committed, reproducible code.

## Operating rules

- **Commit only. Change no code.** Do not edit, reformat, or "improve" anything while committing.
- Group into a few coherent commits by concern, not one giant commit and not one-per-file.
- If something staged looks like it should not be committed (secrets, a stray artifact), **stop and
  flag it** rather than committing it.

## Step 1 — Sanity-check what's staged before committing

- `git status` and `git diff --cached --stat`. Confirm the staged set is what's expected:
  - backend fixes: `__main__.py`, `ads_spend.py`
  - S8/S9 guard work: `drift_bands.py`, `reconcile.py`, `reconcile_au.py`, `attribution.py`
  - the `ad_spend_history` migration
  - the locked-targets change (in `reconcile.py`)
  - docs: `reference/data/*.md`, `reference/prompts/*.md`
- **Flag, do not commit, anything that shouldn't be there:** `.env` or secrets, `.DS_Store`, the scratch
  table dumps, or large backup CSVs if they weren't intended for git. Report and wait.
- Add `.DS_Store` to `.gitignore` (and unstage it if staged) so it stops reappearing.

## Step 2 — Commit in coherent groups

Suggested boundaries (adjust if the staged reality differs — report if so):

1. **backend pipeline fixes** — `__main__.py` entrypoint KeyError + `ads_spend.py` per-currency routing
   (B1–B4). One commit; message notes the pipeline now runs end to end and the ads loader is reproduced.
2. **guard: pin semantics under ingestion (S8) + ads horizon (S9)** — `drift_bands.py`, `reconcile.py`,
   `reconcile_au.py`, `attribution.py`, migration `f6a7b8c9d0e1` / `ad_spend_history`. Message notes
   pins survive ingestion via as-of horizon; `DEFECT_REMEASURED` added.
3. **guard: locked-target grading** — the PASS / ACCEPTED_DRIFT / FAIL change. Message notes US exits 0
   on restatement, still FAILs on regression; decision-A zeros stay exact.
4. **docs + prompt archive** — `reference/data/*.md` audit/findings and `reference/prompts/*.md`. Message
   notes these are the decision record and are cited as evidence in the audit.

If the migration must accompany its code to keep the tree runnable at every commit, fold it into (2)
rather than splitting it out.

## Step 3 — Verify clean

- After committing, `git status` shows a clean working tree (only `.DS_Store` ignored).
- `git log --oneline -5` shows the new commits.
- Confirm the tree still builds/imports at HEAD (a quick `python -c "import sync"` or equivalent) so no
  commit left it in a broken state.
- Do **not** push unless asked; committing is the ask.

## Guardrails

- No code, config, or doc content changed — this is purely `git add`-already-done + `git commit`.
- Never commit secrets or `.env`. If staged, stop and report.
- Do not squash away the S8/S9/locked-target history into one commit; the boundaries are the point.
- Do not push.

## Definition of done

- Staged set reviewed; anything that shouldn't be there flagged (not committed).
- `.DS_Store` gitignored.
- A few coherent commits made along the boundaries above (or the reported adjusted ones).
- Clean working tree; tree imports at HEAD; new commits shown. No push, no code change.