# Claude Code Task — Verify the remaining +$3.6k net residual, then close out US (no fixing unless a label fails)

## Context

The refund-COGS fix closed the systematic residual: cumulative net Δ went from −$8,042
(flat-negative, systematic) to **+$3,568 (+1.7% of Sellerise net)** — now a scatter of small
per-month deltas with mixed signs, the signature of genuine boundary/timing noise rather than a
bug. The fix is correct and built. This task does **not** add more fixing. It **verifies the
labels** on what's left, then produces a close-out decision.

Post-fix residual by month, with the label each currently carries:

| month | net Δ | current label |
|---|---|---|
| Jan | +1,440 | pre-backfill boundary |
| Feb | +1,527 | pre-backfill boundary tail |
| Mar | +743 | "small refund-policy sub-difference" |
| Apr | +688 | "same" |
| May | +11 | essentially exact |
| Jun | −841 | trailing-month snapshot effect |

Two of these labels are asserted, not proven. This project has twice had a plausible label turn
out wrong (the −$1.46 "V2 boundary" and the −$8k "attribution drift"), so verify before accepting.

## Operating rules

- **Verify, don't fix.** Do not change net math, mappings, COGS, or attribution. Confirm or
  falsify the labels using data already in the DB/report.
- Report actual numbers per check. If a label holds, accept and document. If it fails, stop and
  report — do not auto-fix.

## Check 1 — Mar/Apr "refund-policy sub-difference" (the soft label — verify first)

This is the least-tested label: +$743 / +$688, same-signed, two adjacent **settled** months. Name
the actual mechanism.

- Decompose Mar and Apr net Δ per bucket (same method as the prior diagnosis). Confirm which
  bucket(s) carry the ~$700 — if it's not `refundsObject`/`cog`, the "refund-policy" label is
  wrong.
- If it is refund-related: quantify the specific sub-difference. Candidates to distinguish:
  Sellerise nets refund COGS at a **different unit basis** (e.g. restocked-and-resellable units
  only, not all returned units); or a refund reason code Sellerise treats differently; or a
  `cog_per_sku` rate difference on the returned SKUs vs shipped.
- Verdict: either a **named** mechanism with numbers, or "not refund-policy — actual cause is X."
  Do not leave it as "sub-difference."

## Check 2 — Jan/Feb pre-backfill boundary (verify + size the recoverable amount)

The Jan/Feb residual is claimed to be Dec-2025 orders you don't have full history for. This is
testable, and the test doubles as the input to the scope decision below.

- Identify the transactions contributing the Jan/Feb Δ and confirm they trace to orders with
  PurchaseDate **before 2026-01-01** (or refunds of such orders). If yes, the label holds and the
  amount is structurally unrecoverable *without* extending the backfill window.
- Quantify how much of the +$2,967 (Jan+Feb) is pre-window-order-linked vs anything else. That
  figure is exactly what a backfill extension would recover — record it.

## Check 3 — Jun trailing-month (confirm it's the accepted cutoff, not new)

- Confirm Jun's −$841 traces to refunds processed after Sellerise's snapshot date (the same ~48h
  cutoff already accepted on the P&L side), i.e. it should shrink as June settles. A quick check:
  are the Jun-contributing refunds dated near/after the Sellerise snapshot cutoff? If yes, accept;
  if they're mid-June, the label is wrong.

## Close-out decision (the deliverable)

After Checks 1–3, write the accept-vs-extend recommendation:

- **If all three labels hold:** recommend **accept** the +$3.6k (+1.7%) as documented, quantified,
  per-cause residual. The specialist has approved "accurate, not exact," and every dollar is now
  named — no unexplained residual remains. US reconciliation is complete.
- **Scope input:** state the Jan/Feb pre-window-recoverable figure from Check 2, and the cost of
  recovering it (extend the backfill to ~Nov–Dec 2025: re-pull transactions + orders for that
  window, re-attribute). Recommend whether that ~$3k of boundary noise justifies extending a
  locked scope decision, or whether it's better left as an accepted boundary artifact.
- **If any label fails Check 1–3:** report the real cause with numbers; do not fix in this task —
  the fix (if warranted) becomes a separate follow-up.

## Definition of done

- Checks 1–3 run with per-bucket / per-transaction numbers; each label confirmed or replaced with
  its evidenced cause.
- `reference/data/net_residual_diagnosis.md` updated: Mar/Apr and Jun labels made precise, Jan/Feb
  recoverable amount quantified.
- A written accept-vs-extend recommendation for US close-out.
- No net math, mapping, COGS, or attribution changed in this task.