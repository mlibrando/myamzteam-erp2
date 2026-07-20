# Task: Implement Phases 2–3 of the P&L fixes (with two mandatory pre-ship verifications)

Phase 1 is approved and the diff shape is correct. Implement Changes 1–3 below. The two
verifications are mandatory: V1 guards against a silent regression, V2 against a silent no-op.
Stop after Phase 3 with the reconciliation report — do **not** treat the new profit number as
final until Elena has reviewed the bridge. Stay in the aggregation/presentation layer only;
extraction, schema, and reconcile are untouched.

## Decisions (resolved — implement exactly as stated)
- **Change 3 = rename `NET_ROW` "Net" → "Profit".** Do not add a second row; post-fix Net and
  Profit are numerically identical and a duplicate is clutter. Update the frontend `isNet`
  reference (page.jsx:167) to match "Profit".
- **Keep Sales tax-inclusive** and book the offset as a cost in Selling Fees (the approach from
  your Phase 1 diff). Do not strip tax out of the Sales row.
- **Sellerise: do not force a tie.** Produce a reconciliation bridge instead (Phase 3).

## Change 1 — dedupe reimbursement reversal (reclassification, ZERO profit impact)
Route the reversal leaf into Reimbursements so it nets against money-in.

**V1 (mandatory — guards a regression):** your proposed `REIMB_PREFIX = "FBAInventoryReimbursement."`
has a trailing dot, so it matches only the reversal leaf
`FBAInventoryReimbursement.FBAReversedReimbursement`. If the money-in leaf key is exactly
`FBAInventoryReimbursement` (no trailing segment), then
`"FBAInventoryReimbursement".startswith("FBAInventoryReimbursement.")` is **False** and money-in
falls through to Operational Fees — a regression.
- Print the exact string of BOTH leaf keys (money-in and reversal) before editing.
- Match both explicitly. Prefer an explicit set `{<money_in_key>, <reversal_key>}` over a fuzzy
  prefix. If you keep a prefix, drop the trailing dot and confirm it doesn't over-match any other
  `expenses` leaf.
- After the change, assert money-in STILL lands in Reimbursements.

**Self-check (US 2026-01):** Operational Fees delta = +1,037.16, Reimbursements delta = −1,037.16
(equal and opposite); total Profit unchanged by this change. AU: unchanged (no reversal leaf).

## Change 2 — fold tax into Selling Fees (the ONLY profit-moving change)
Book −salesTaxes into Selling Fees, offsetting the +tax already carried in Sales. Reuse
`_SALES_TAX_LINES` from reconcile; keep Sales as-is.

**V2 (mandatory — guards a silent no-op):** the clause
`if bucket == "chargesObject" and line_key in _SALES_TAX_LINES` only fires if pnl.py iterates
`chargesObject` at leaf granularity with `line_key` exactly `"Tax"`/`"ShippingTax"`/`"GiftWrapTax"`.
- Print the `chargesObject` line_keys pnl.py actually sees; if they are compound or flat, adjust
  the match so it triggers.
- After the change, assert the Selling Fees delta equals −salesTaxes per marketplace:
  US −9,033.01 · CA −890.66 · UK −2,127.82 · AU −44.78. Any delta of 0 means the match didn't fire
  — fix before proceeding.

Audit note: the offset uses reconcile's `salesTaxes` (buyer-collected) for consistency with the
reconcile net formula, not the raw facilitator passthrough bucket. These differ by ~$5/mo
(US: 9,033.01 vs 9,027.50) — immaterial and deliberate.

## Change 3 — rename Net → Profit
`NET_ROW = "Profit"`; the existing column-sum logic already computes it from the corrected rows.
Update the frontend `isNet` reference (page.jsx:167) and remove the now-resolved provisional
Operational/Reimbursements note (page.jsx:207-214).

## Phase 3 — verify, bridge, then stop
1. Confirm the V1 and V2 self-checks pass for all four marketplaces (NA, CA, UK, AU).
2. **Sellerise bridge (US, 2026-01):** produce an explicit line-by-line bridge from Sellerise net →
   dashboard Profit, quantifying each difference — the tax treatment, and the
   operational-fees/reimbursements bucket (~+$10k) that Sellerise excludes. Do not adjust numbers
   to force a tie; the point is a legible explanation of the gap so Elena can confirm the intended
   definition of "Profit."
3. Report how dashboard "Sales" compares to Sellerise's sales row (tax-inclusive here), so any
   sales-line display mismatch is on record.
4. Append all three changes to `reference/data/decisions_audit.md`, explicitly recording that the
   profit impact is entirely from Change 2 (tax), Change 1 is profit-neutral, and the ~$9k/mo US
   reduction is the correction of previously-omitted tax passthrough.

Stop after Phase 3. Flag the profit swing prominently for Elena's sign-off before it is treated as
final. Keep the final diff small and localized (~12 lines backend, ~2 lines frontend).