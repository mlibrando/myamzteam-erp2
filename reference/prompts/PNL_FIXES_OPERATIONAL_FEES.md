# Task: Three P&L fixes (dedupe operational fee, fold taxes into selling fees, add profit row)

MYAMZTEAM multi-marketplace P&L (Amazon SP-API Finances v2024-06-19). Three changes confirmed
with Elena. All three are **aggregation / presentation-layer** edits over data the pipeline
already parses and reconciles — do **not** touch extraction, the DB schema, or the reconciliation
logic. No new Amazon API surface is introduced, and no new documentation lookup is required: the
Finances v2024-06-19 model is already the source, and `breakdownType` is a free-form string, so
whatever your parser already classifies as tax is the source of truth.

## Ground rules
- **Investigate before editing.** Do Phase 1 fully and report findings + the proposed minimal diff
  BEFORE changing anything.
- Minimalist. No new files, deps, abstractions, or refactors. The likely footprint is a handful of
  lines in the P&L assembly function plus one dashboard component.
- Do not reintroduce or collide with the pending dashboard FX/fees fix. Leave FX handling alone.

## Phase 1 — Investigate (read-only, then stop and report)
Find and report, with file paths and line references:
1. Where raw Finances line items are mapped into P&L sections (Sales, Selling Fees, Operational
   Fees, Reimbursements). This is likely a mapping dict or a categorization function in the backend.
2. The "operational fee" item that currently appears in **both** the Operational section and
   Reimbursements — the exact key/identifier and both places it is emitted or rendered.
3. How taxes are handled today: which `breakdownType` values your parser treats as tax, and where
   that amount currently lands in the P&L (its own line? operational? uncategorized?).
4. Where section subtotals and the overall P&L response are assembled (FastAPI response shape) and
   where they render (Next.js dashboard component).
5. The sign convention for cost lines and for reimbursements (stored positive vs negative). Report
   it explicitly — the profit math depends on it.

Then propose the minimal diff and wait.

## Phase 2 — Changes
1. **Dedupe operational fee.** Remove the operational fee line from the Operational section; keep it
   only under Reimbursements. Expect this to be a single deleted mapping entry / render line, not a
   restructure.
2. **Fold taxes into Selling Fees.** Include the tax amount in the Selling Fees total. If a separate
   Taxes line currently exists, merge/remove it so the amount is counted once, not double-counted.
   Reuse the parser's existing tax classification — do not re-derive which breakdown types are tax.
3. **Add a Profit row.** Profit = total sales − sum of all cost line items, at the bottom of the
   P&L. Implement this **after** changes 1 and 2 so it sums the corrected lines, and compute it from
   the already-assembled section totals — do not recompute from raw transactions. Respect the sign
   convention found in Phase 1 (in particular, reimbursements are a credit and must reduce net cost
   / add to profit, not be subtracted as a cost).

## Phase 3 — Verify
- Reconcile one marketplace (US) against Sellerise: Selling Fees now includes tax, Operational no
  longer double-counts the op fee, and the Profit row ties to Sellerise's profit figure.
- Confirm all four marketplaces (NA, CA, UK, AU) render the Profit row.
- Confirm extraction and DB layers are untouched.
- Append the three changes to `reference/data/decisions_audit.md`.

Keep the final diff small and localized.