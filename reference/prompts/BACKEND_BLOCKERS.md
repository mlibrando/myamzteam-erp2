# Claude Code Task — Fix the three backend blockers so the pipeline runs end to end

## Context

Reconciliation is **done**: US, CA, UK, AU all reconcile, every residual closed or pinned as
`KNOWN_TARGET_DEFECT` with evidence. What does **not** work is the pipeline itself. The audit found
three entangled blockers — all touch the same run and the same tables, so they go together.

1. **`sync/__main__.py:94` crashes on every marketplace.** It reads `agg_stats["groups"]`;
   `aggregate_marketplace` never returns that key. The `KeyError` fires **after** Phase 2 commits
   `pnl_monthly` writes and **before** Phase 3 runs COGS. `python -m sync` has never completed for any
   marketplace. This is also the mechanism that produced blocker 3.

2. **The ads loader that produced the reconciled CA/UK/AU numbers is not in the repository.**
   `ads_spend.py:140` drops every row where `budgetCurrency.value != "USD"`, and it is the only writer
   of `ad_spend_daily`. But `reconcile.py:336` reads `'CAD'`/`'GBP'` and `reconcile_au.py` reads
   `'AUD'`. Write set and read set do not intersect for three marketplaces — yet the reports show
   correct `adExpenses`. Some uncommitted script wrote those rows (proof: CA+UK+AU share an `as_of`
   to the microsecond in all six months; per-currency row counts match the raw NA report exactly).
   **Running the committed `ads_spend.py` against CA/UK/AU today would `DELETE` the reconciled rows
   and insert USD rows the readers never select.**

3. **`pnl_monthly` CA cog is stale and mislabeled.** It stores **$10,749.76** across 2025-12→2026-06
   where the override computes **$8,324.18** (+$2,425.58, **+29.1%**), and all seven rows carry
   `currency = 'USD'` while holding a CAD-scale value (hardcoded literal, not `cog_currency()`).
   Zero blast radius today — `reconcile.py` computes cog in memory and never calls `load_pnl`. **Total
   blast radius for the dashboard**, which `PLAN.md:372` specifies reads `pnl_monthly` only.

## Operating rules

- **Simplicity.** Three fixes, no refactor. No new abstractions, no new dependencies, no "while I was
  in there."
- **The reconcile reports are the source of truth.** They are correct today. Any change that moves a
  reported number is a regression, not a fix.
- **Back up before writing.** `ad_spend_daily` holds reconciled rows produced by code that no longer
  exists. Losing them is unrecoverable.

## Step 0 — Protect what can't be regenerated

- **Before any code runs**, dump `ad_spend_daily` (all marketplaces, all months) and the current
  `pnl_monthly` to files under `reference/data/backups/`. These rows are the only surviving output of
  the missing loader.
- Capture the four canonical reconcile reports as the golden baseline for the byte-identical check.
- **Do not run the committed `ads_spend.py` against any marketplace** until Step 2 is done and verified.

## Step 1 — Fix the entrypoint (`__main__.py:94`)

- `aggregate_marketplace` never returns `groups`. Either return it or stop reading it — pick whichever
  is smaller and matches what the log line actually needs. **Do not redesign the return shape.**
- Run `python -m sync --marketplace US` end to end. It must complete all phases. Then CA, UK, AU.
- **Verify:** after a full run, the four reconcile reports are byte-identical to the golden baseline
  (modulo `Generated` timestamps). If any number moves, stop — the pipeline is writing something
  reconcile currently computes in memory, and that's a finding, not a fix.

## Step 2 — Reproduce the ads loader in committed code

- Make `ads_spend.py` write **per-marketplace native currency** rows matching what the readers select:
  US→USD, CA→CAD, UK→GBP, AU→AUD. The report already returns all four currencies (per-currency row
  counts verified against the raw NA report); the bug is the `!= "USD"` filter at line 140.
- Keep the existing `as_of` handling and the idempotent replace semantics.
- **Verify against the backup, not against Sellerise:** regenerate `ad_spend_daily` into a **scratch
  table**, and diff it against the Step-0 backup per (marketplace, month, adProduct). It must reproduce
  the reconciled rows **to the cent**. Only then let it write the real table.
- If it does **not** reproduce them, stop and report. Do not overwrite the backup rows with numbers you
  cannot verify.
- Sanity: the reconciled ad totals are already known-good (CA/UK matched Sellerise to the cent; AU
  matched Sellerboard). Those are your targets.

## Step 3 — Rebuild `pnl_monthly` cog

- Only after Steps 1–2. The pipeline is what writes this table, so it must run correctly first.
- Rewrite CA's cog rows using the override (`MARKETPLACE_COG_SOURCE_OVERRIDE`), and set `currency` from
  `cog_currency()` rather than the hardcoded literal. Expect CA to go **$10,749.76 → $8,324.18**.
- Relabel UK's cog rows `USD → GBP` (S7 landed; `cogs.py:253` writes this and hasn't been re-run).
- **Verify:** `pnl_monthly` cog now equals what `reconcile.py` computes in memory, per marketplace per
  month. That equality is the whole point — it is what makes the table safe for the dashboard to read.
- Reports must still be byte-identical to the golden baseline.

## Guardrails

- **Never run the committed `ads_spend.py` against CA/UK/AU before Step 2 is verified** — it deletes
  reconciled rows.
- Back up `ad_spend_daily` and `pnl_monthly` before the first write. Non-negotiable.
- No reported number may move. The reports are correct; the pipeline is what's broken.
- Do not touch reconciliation math, attribution, bucket maps, bands, or the `KNOWN_TARGET_DEFECT`
  registry.
- Do not "improve" `aggregate_marketplace`'s return shape, the ads schema, or `pnl_monthly`'s columns.
- `pnl_monthly_snapshots` is append-only — a rebuild must not rewrite history.

## Definition of done

- `python -m sync --marketplace {US,CA,UK,AU}` each complete end to end, no `KeyError`.
- `ads_spend.py` writes native-currency rows that reproduce the Step-0 backup **to the cent**; readers
  in `reconcile.py` / `reconcile_au.py` select them unchanged.
- `pnl_monthly` cog equals reconcile's in-memory figure for every marketplace/month, with correct
  `currency` labels (CA CAD-scale value fixed to the override's USD basis; UK relabeled GBP).
- Four reconcile reports byte-identical to the golden baseline (timestamps excepted); exit codes
  unchanged (UK 0, AU 0, CA 0, US 1 pre-existing).
- Backups written before the first mutation; no snapshot history rewritten.