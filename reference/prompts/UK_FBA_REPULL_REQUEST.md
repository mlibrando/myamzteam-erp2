# Claude Code Task — Test the UK FBA label (S2): restatement, or a netting difference?

## Context

UK's five `fbaObject` cells carry a **−$458** same-signed gap vs Sellerise, labeled *"Amazon
post-snapshot restatement drift."* **That label has never been tested.** The only pull-to-pull evidence
was a **36-second** re-pull — restatement happens over days/weeks, so 36 seconds cannot observe it.

S2 is the last unverified claim in the project and the only thing keeping `reconcile --marketplace UK`
at exit 1 (its other 4 cog cells are now pinned as `KNOWN_TARGET_DEFECT`).

The test is **Amazon vs Amazon**, not Amazon vs Sellerise. The claim is that *Amazon's* numbers changed
after Sellerise snapshotted them. So: does Amazon's FBA figure for an old UK month differ today from
what we stored months ago? Sellerise's file is frozen and is not part of this test.

Note the discriminator: **restatement moves on re-pull; a basis/netting difference does not.**

## Operating rules

- **Simplicity.** One re-pull, one diff, one fallback test. No new machinery, no engine changes.
- Read-only against `sp_transactions` — do **not** overwrite the stored original rows; they are the
  "before" snapshot and the whole basis of the test.
- Name the result by test. If neither hypothesis fits, say so; do not pick the tidier one.

## Step 0 — Confirm the "before" snapshot still exists

- Check whether `sp_transactions` still holds the **original** UK rows (raw JSON, original `as_of` /
  ingest timestamp) for a settled month (Feb or Mar 2026), or whether a later idempotent sync replaced
  them.
- If the original bytes are intact → run Step 1 today.
- If they were overwritten → say so plainly. The test becomes forward-looking (pull now, re-pull in ~2
  weeks). Do not fake a "before" from a later pull.

## Step 1 — Re-pull and diff (the actual test)

- Re-pull one settled UK month (Feb 2026 preferred; Mar as backup) via `FinancesV20240619.list_transactions`
  into a **scratch location** — never into `sp_transactions`.
- Diff the FBA leaves (`FBAPerUnitFulfillmentFee`, `FBAFees`) between the stored original and the fresh
  pull: totals, per-transaction, and count of transactions present in one but not the other.
- Read it:
  - **Moved** (materially, in the direction that closes −$458) → restatement confirmed. The label stands.
  - **Byte-identical / moved by cents** → Amazon did **not** restate. The label is refuted. Go to Step 2.
  - **Moved, but not toward the gap** → restatement exists but doesn't explain −$458. Report both facts;
    do not credit the label.

Report the actual numbers either way. (For calibration: Sellerboard restates only the trailing settled
month, by ≈$0.10; Amazon's own restatement magnitude on UK is what this measures.)

## Step 2 — Only if refuted: test the netting hypothesis

Sellerise already nets refunded units out of `cog`. The natural analog: **Sellerise may compute its FBA
line net of FBA fee refunds/reimbursements on returned units**, which would make its FBA figure smaller
than our gross — a stable, same-signed gap, exactly the shape observed.

- Identify FBA fee refund / reimbursement components in the UK transactions (FBA fee reversals on Refund
  transactions, `FBAInventoryReimbursement`-type leaves, or negative FBA components).
- Test: does `our_gross_FBA − those_reimbursements ≈ Sellerise fbaObject`, per month, across the settled
  months? Sum |Δ| before and after.
- If it closes the −$458 across months → **mapping/netting finding** (fixable). Report the specific
  leaves; do not apply the fix in this task.
- If it doesn't → the −$458 is neither restatement nor this netting. Report it as **unexplained,
  same-signed**, and leave it as `INVESTIGATE`. Do **not** pin it.

## Guardrails

- Do **not** pin the FBA cells as `KNOWN_TARGET_DEFECT` unless Step 1 confirms restatement with numbers.
  Pinning an untested inference is exactly what the last task correctly refused to do.
- Do not widen any band; do not force UK to exit 0.
- Do not write to `sp_transactions`, `pnl_monthly`, or any snapshot table. Scratch only.
- Do not touch US/CA/AU. Do not run the committed `ads_spend.py` against anything (it would DELETE
  reconciled CAD/GBP/AUD rows).
- A same-signed material residual stays systematic until a test names it. `Unexplained` is a valid,
  honest outcome.

## Definition of done

- Stated plainly whether the original "before" rows exist; if not, the test is deferred, not faked.
- Step 1 diff reported with real numbers: did Amazon's UK FBA figures move between pulls, and by how much?
- Verdict: **restatement confirmed** (pin the cells, UK may exit 0), **refuted → netting finding** (report
  the leaves, fix in a separate task), or **refuted → unexplained** (stays `INVESTIGATE`).
- No data written, no band widened, no cell pinned without evidence.