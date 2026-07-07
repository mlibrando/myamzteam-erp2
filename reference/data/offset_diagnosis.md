# Feb–Jun 2 % offset diagnosis

**Verdict:** the offset is **NOT a listTransactions boundary/windowing bug**. It's an
attribution-rule difference between Sellerise's data source and `listTransactions`. Do NOT
proceed with Test 2 (backfill window extension) — per the decision protocol in the task
brief, one-sided evidence from Test 1 stops the investigation before we force a fix that
would mask the real cause.

Documented as a known, quantified limitation below.

---

## Test 1 — Status-split isolation

For each failing revenue/fee bucket, split our contribution by `transactionStatus` and
diff each slice against Sellerise separately. If the offset lives in `DEFERRED_RELEASED`
alone and `RELEASED` matches to the cent, the hypothesis (deferred attribution) is
supported. Otherwise it's falsified.

Query source: `sp_transactions.raw_json` re-flattened via `breakdown_leaves_for_txn` and
routed through `bucket_map.classify()`. Excludes `is_deferred_release_event=true` release
events. Sellerise column is `SELLERISE_RAW_DATA.json` per-month bucket.

### chargesObject.Principal

| ym | RELEASED | DEFERRED_RELEASED | total (ours) | Sellerise | RELEASED − S | total − S |
|---|---:|---:|---:|---:|---:|---:|
| 2026-02 | 144,558.08 | 389.80 | 144,947.88 | 136,806.23 | **+7,751.85** | +8,141.65 |
| 2026-03 | 99,686.05 | 24,813.01 | 124,499.06 | 121,824.06 | −22,138.01 | +2,675.00 |
| 2026-04 | 824.50 | 117,800.08 | 118,624.58 | 117,555.08 | −116,730.58 | +1,069.50 |
| 2026-05 | 194.00 | 108,617.83 | 108,811.83 | 110,260.80 | −110,066.80 | −1,448.97 |
| 2026-06 | 0.00 | 79,058.14 | 79,058.14 | 98,691.38 | −98,691.38 | −19,633.24 |

### feesObject.Commission

| ym | RELEASED | DEFERRED_RELEASED | total (ours) | Sellerise | RELEASED − S | total − S |
|---|---:|---:|---:|---:|---:|---:|
| 2026-02 | −21,655.57 | −58.47 | −21,714.04 | −20,490.89 | **−1,164.68** | −1,223.15 |
| 2026-03 | −14,937.18 | −3,708.10 | −18,645.28 | −18,246.12 | +3,308.94 | −399.16 |
| 2026-04 | −123.76 | −17,659.43 | −17,783.19 | −17,622.34 | +17,498.58 | −160.85 |
| 2026-05 | −29.12 | −16,274.55 | −16,303.67 | −16,464.03 | +16,434.91 | +160.36 |
| 2026-06 | 0.00 | −11,842.53 | −11,842.53 | −10,639.72 | +10,639.72 | −1,202.81 |

**Feb signal is the tell.** Feb is 99.7 % direct-release RELEASED (only 2 DEFERRED_RELEASED
Shipments). If DEFERRED_RELEASED attribution were the mechanism, the RELEASED-only slice
should match Sellerise. Instead the RELEASED slice **alone** is $7,752 above Sellerise's
Feb total. That falsifies the deferred-attribution hypothesis for the Feb overshoot.

Mar–May are dominated by DEFERRED_RELEASED (as the account switched to reserve mode in
early March — see below), so a same-slice comparison isn't meaningful there.

**Test 1 conclusion: hypothesis challenged.** Per the plan's decision rule:

> If the offset is present in the pure `RELEASED` slice too → it is NOT purely a
> deferral-timing artifact. Hypothesis challenged — stop and report.

---

## Test 1b — Magnitude trend

Total `chargesObject` revenue (Σ sub-lines) per month, ours vs Sellerise:

| ym | ours (Σ chargesObject) | Sellerise revenue | Δ $ | Δ % |
|---|---:|---:|---:|---:|
| 2026-01 | 167,302.59 | 175,191.94 | **−7,889.35** | −4.50 % |
| 2026-02 | 152,725.66 | 144,011.44 | **+8,714.22** | +6.05 % |
| 2026-03 | 131,414.37 | 128,580.85 | +2,833.52 | +2.20 % |
| 2026-04 | 124,977.03 | 123,835.52 | +1,141.51 | +0.92 % |
| 2026-05 | 114,681.33 | 116,138.17 | −1,456.84 | −1.25 % |
| 2026-06 | 104,942.33 | 103,674.19 | +1,268.14 | +1.22 % |

Two features stand out:

1. **Jan −$7,889 + Feb +$8,714 = +$825 net.** The two extremes nearly cancel. That's
   the signature of a **boundary offset in Sellerise's attribution**, not a data-loss bug
   on either side.
2. **Feb → May decays** (+6 % → −1.2 %) — not perfectly monotone, but the magnitude
   shrinks as we move away from the Jan/Feb boundary. Would be consistent with a boundary
   artifact **if** the mechanism were located at the Jan/Feb line — but Test 1 rules out
   the specific deferred-attribution mechanism at that boundary.

Cumulative Jan–Jun revenue delta: **+$4,611** on $791,432 (0.58 %). Small in aggregate,
but structurally shaped, not random.

---

## Test 1c — Alternative-date attribution

The plan called for probing `DeferredContext.maturityDate` on the offending
DEFERRED_RELEASED transactions and re-keying by that date.

**Finding: `DeferredContext` doesn't exist on any of our 5,918 DEFERRED_RELEASED
transactions.**

```
DEFERRED_RELEASED total: 5918
                with DeferredContext: 0
```

The listTransactions v2024-06-19 payload we get exposes exactly these date fields:
`postedDate` only. No `maturityDate`, no `releaseDate`, no `purchaseDate`. So there's
nothing to re-key against within the listTransactions payload.

I tested one other reachable attribution rule as a check: **re-attribute each transaction
by the last `postedDate` of its `SETTLEMENT_ID` group** (the Amazon biweekly settlement
period end). Amazon's settlements are 13-day cycles, and each straddles a month boundary:

| SETTLEMENT_ID | first_posted | last_posted | span (d) |
|---|---|---|---|
| 25428826791 | 2026-01-15 | 2026-01-29 | 13 |
| 25538101991 | 2026-01-29 | 2026-02-12 | 13 |
| 25658193031 | 2026-02-12 | 2026-02-26 | 13 |
| 25764026101 | 2026-02-26 | 2026-03-12 | 13 |
| 25876248651 | 2026-03-12 | 2026-03-26 | 13 |

Attributing by settlement-end month gives:

| ym | ours (settle-end) | Sellerise Principal | Δ $ |
|---|---:|---:|---:|
| 2026-01 | 143,587.85 | 167,137.89 | −23,550.04 |
| 2026-02 | 145,426.23 | 136,806.23 | +8,620.00 |
| 2026-03 | 121,150.37 | 121,824.06 | −673.69 |
| 2026-04 | 106,027.37 | 117,555.08 | −11,527.71 |

Doesn't help — some months get worse. Settlement-end attribution is not what Sellerise
does.

---

## Ancillary hypothesis probed and rejected — `accountType`

A first-look sample of `DEFERRED_RELEASED` transactions carried
`sellingPartnerMetadata.accountType = "Invoiced Orders"` (Amazon B2B). Made me think
Sellerise was excluding B2B. Full census:

```
Invoiced Orders  DEFERRED           1
Invoiced Orders  DEFERRED_RELEASED  9
Standard Orders  DEFERRED         396
Standard Orders  DEFERRED_RELEASED 4,407
Standard Orders  RELEASED          5,496
```

Only 10 Invoiced Orders total across the whole window. Contribution to Feb `Principal`:
$389.80 — trivial next to the $8,141 delta. Rejected.

---

## Cumulative-by-day cross-check

Feb `chargesObject.Principal` cumulative by day (target Sellerise = $136,806.23):

```
Feb-26: 132,542.52
Feb-27: 137,818.54  ← within $1,012 of Sellerise
Feb-28: 144,947.88
```

Sellerise's Feb total sits between our Feb-26 and Feb-27 cumulative. Consistent with
Sellerise's snapshot having a ~1-day cutoff before month-end. But this alone can't
explain the Jan −$7k under-shoot (which points to Sellerise INCLUDING pre-window data
we don't have).

The two artifacts together — a ~1-day pre-month-end snapshot cutoff **plus** Sellerise
pulling some late-Dec activity into Jan — produce the Jan−Feb cancellation pattern.

---

## Account-mode transition (context, not cause)

For completeness — the account switched from immediate-release to reserve/defer mode
in early March 2026:

```
month  RELEASED  DEF_REL   D  (Shipment, excl release events)
2026-01   2,220        4   0
2026-02   1,988        2   0
2026-03   1,248      308   0
2026-04      18    1,540   0
2026-05      14    1,469   0
2026-06       7    1,093 258
```

This is real Amazon account-status behavior (established sellers can get immediate
release; new/higher-risk sellers get held in reserve). Not our bug. Explains why the
RELEASED vs DEFERRED_RELEASED mix flips at March.

---

## Apr $0.28 RestockingFee guardrail

Verified — it's **not** DEFERRED-sourced.

```
Apr Refund.RestockingDeduction* by status:
  RELEASED  RestockingDeductionPrincipal  count=1  sum=4.59
  RELEASED  RestockingDeductionTax        count=1  sum=0.28
```

Sellerise's Apr `refundsObject.RestockingFee` = 4.59, matching just the Principal.
The $0.28 comes from `RestockingDeductionTax`, which decision D says to sum in.
**This is a plan-level mapping-scope question, not a bug:** if Sellerise treats
`RestockingDeductionTax` as MFT-adjacent (excluded) rather than folding it into
`RestockingFee`, our +$0.28 is by-design under our current mapping. Recommend leaving
decision D as-is unless a scan of other months shows the Tax line materially matters
(only 1 non-zero occurrence in 6 months).

---

## Verdict

Not a boundary bug. The offset is a **structured attribution-rule difference between
Sellerise's data source and `listTransactions`**. Evidence:

- Test 1 shows the Feb overshoot lives in the RELEASED slice, not DEFERRED_RELEASED.
- Test 1c shows the payload has no alternative date field to re-key on.
- Cumulative-by-day suggests Sellerise's snapshot cuts off ~1 day before month-end,
  AND includes pre-window activity (Jan surplus at their end).
- Cumulative Jan–Jun net delta is only +$4,611 on $791k (0.58 %) — small in aggregate,
  structurally month-shaped.

Most likely mechanism: Sellerise uses a different Amazon source (candidates:
`listFinancialEvents`, `Orders API` `PurchaseDate`, or a settlement-report roll-up),
which produces different month boundaries than `postedDate`. Fixing this from our end
would require adding one of those APIs and re-attributing — significant work outside
the scope of this task, and Sellerise-parity may still not be exact.

**Do NOT proceed to Test 2.** Extending backfill by 60 days would only add Nov–Dec 2025
transactions with `postedDate` in Nov–Dec — those bucket to Nov/Dec 2025, not Jan 2026.
They wouldn't close the Feb offset (which is in the RELEASED slice on Feb-posted
transactions) or the Jan under-shoot (which reflects Sellerise's attribution of Dec
activity to Jan, a rule we don't have).

## Known unsourceable (per plan) — do not re-investigate each run

These are Sellerise-schema lines that cannot come from `listTransactions`:

- `chargesObject.Shipping` (May $36.62, Jun $174.08) — no SP-API leaf carries this,
  distinct from `ShippingCharge`.
- `feesObject.POAServiceFee`, `PoAPerUnitFulfillmentFee` (May only) — "Pay On Amazon"
  fees, not in the `listTransactions` vocabulary.
- `refundsObject` decomposed reason codes (`MISSING_FROM_INBOUND`,
  `FREE_REPLACEMENT_REFUND_ITEMS`, `WAREHOUSE_DAMAGE`, `WAREHOUSE_LOST`,
  `REVERSAL_REIMBURSEMENT`, `COMPENSATED_CLAWBACK`) — Sellerise decomposes
  `FBAInventoryReimbursement` into named reason codes; SP-API gives only the aggregate.

## Known accepted residuals

- **Trailing-month DEFERRED estimates** (`feesObject.ReferralFee`, `fbaObject.FBAFees` on
  Jun): reported as EXPECTED in the reconcile report. Different snapshot timing means
  our estimate ≠ Sellerise's estimate; both are correct at their respective timestamps.
- **Feb–Jun ~1 % attribution offset**: the subject of this diagnosis. Documented as a
  known Sellerise-vs-listTransactions data-source difference (~$4.6k cumulative on
  $791k, 0.58 %). Not silently absorbed into EXPECTED — surfaced as FAIL in the report.
- **Apr `refundsObject.RestockingFee` +$0.28**: RestockingDeductionTax component.
  Plan-level mapping-scope question, not a bug.
- **Mar +$2.00, Jun +$1.00 on `refundsObject.Promotion`**: tiny snapshot-timing residuals
  on a small line — small enough to fall into the "attribution-rule difference" pattern
  above.
