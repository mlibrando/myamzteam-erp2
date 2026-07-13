# Claude Code Task — Probe pnl_monthly + prove the bucket→P&L-row mapping (read-only)

## Context

Building the v1 P&L dashboard: a month-as-column grid (rows = P&L line items, columns = months) per
marketplace, with an "All" view in USD. It reads `pnl_monthly`. Before any UI or API is built, confirm
two things: (1) `pnl_monthly`'s real schema, and (2) that the stored buckets can be regrouped into
Elena's six P&L rows and reproduce her manual sheet — **eyes open about where they will not tie, because
the dashboard shows the correct Amazon figures, not Sellerise's.**

**This is read-only.** No schema changes, no API, no UI. Output is one findings doc the dashboard is
built against.

Decisions already locked:
- v1 shows **Amazon-derived rows only**: Sales, COGS, Ad Spend, Selling Fees, Operational Fees, Refunds,
  Reimbursements from AMZ. No Gross Profit / ROAS / Salaries (derived or non-Amazon).
- Currency: **single marketplace → native** (USD/CAD/GBP/AUD); **All → USD**, using Elena's **fixed**
  book rates (GBP 1.34, CAD 0.71, AUD 0.69), kept in config, not hardcoded, labelled as her book rates.
- When the dashboard disagrees with Elena's Sellerise-based sheet, it shows the **correct reconciled
  Amazon figure** — the divergence is the point, not a bug.

## Elena's mapping (Sellerise taxonomy — VERIFY against pnl_monthly's actual leaves)

Her sheet groups Sellerise leaves into six rows. This is a **Sellerise** grouping; your buckets may name
or split leaves differently. Confirm each maps to a real `pnl_monthly` leaf/bucket, and flag any leaf in
her list with no counterpart, and any pnl_monthly leaf her list omits.

- **Sales** ← product sales, tax, promotion, shipping charge, shipping tax, gift wrap (+tax), shipping,
  product charges, liquidations, liquidation adjustments
- **COGS** ← cost of goods
- **Ad Spend** ← sponsored products / brands / display / video / television
- **Selling Fees** ← FBA fees, FBA per-unit fulfilment fee, FBA fees (pending), referral fees,
  commission, shipping/giftwrap chargeback, referral fee (pending), POA service/per-unit fee, digital
  services fee (+FBA, +adjustment)
- **Operational Fees** ← storage fees, amazon fees, premium services, subscription, restocking,
  retrocharge (+reversal), inbound transportation fee (+adjustment), FBA inbound placement, storage
  renewal, compensated clawback, disposal/removal complete, missing-from-inbound clawback, free
  replacement refund items, fee adjustment, other-transaction, reversal reimbursement
- **Refunds** ← refund product sales/tax/commission/promotion/shipping charge/shipping chargeback/
  shipping tax, tax withheld, goodwill
- **Reimbursements from AMZ** ← reversal reimbursement, missing from inbound, warehouse damage,
  warehouse lost, removal order lost

### Three collisions/subtleties to resolve explicitly

1. **`reversal reimbursement` appears under BOTH Operational Fees and Reimbursements in Elena's sheet.**
   This is almost certainly a double-count bug in her sheet (a leaf can't live in two P&L rows); she is
   confirming which she intended. **First check whether your leaves distinguish the two directions:** the
   reconciliation already has `FBAInventoryReimbursement` (money in) AND `FBAReversedReimbursement`
   (reversal/money out) as distinct leaves, and traced UK's set (`MISSING_FROM_INBOUND +
   REVERSAL_REIMBURSEMENT + WAREHOUSE_DAMAGE + COMPENSATED_CLAWBACK` tied to `FBAInventoryReimbursement +
   FBAReversedReimbursement`).
   - **If your leaves DO split by direction:** map the reimbursement leaf → Reimbursements (positive),
     the reversal leaf → Operational Fees (negative). Note that this *resolves* Elena's double-listing —
     her two placements each capture one real direction — rather than overriding it. This is the
     preferred outcome; report it as such for her to confirm.
   - **If it is genuinely one signed leaf that can't be split:** default it to **Reimbursements** for now
     (user's interim call), and mark it **PROVISIONAL — pending Elena's confirmation**, not settled.
   Either way, Reimbursements (money in) and Operational-Fees clawbacks (money out) must not double-count.
2. **Selling Fees carries the known Sellerise defects** (UK GMAKER-3 FBA understated 94%; UK per-SKU
   costs). `pnl_monthly` holds the correct Amazon figure, so **UK Selling Fees will exceed Elena's sheet
   by ~the GMAKER-3 gap. That is expected and correct.**
3. **CA COGS is on a USD basis** (the override) while CA sales are CAD. Confirm what currency
   `pnl_monthly` stores CA cog in, and whether showing it next to CAD sales in the native CA view is
   coherent or needs a display note.

## Step 1 — Schema (read-only)

- Dump `pnl_monthly`'s columns and types. One sample row per marketplace.
- Report: is it one row per (marketplace, month, bucket, sub_line)? Where's the currency recorded? Is
  `net` stored or derived? Are all four marketplaces × all settled months present?
- List the distinct buckets/leaves actually stored, per marketplace.

## Step 2 — Prove the mapping on one month, by marketplace

- Regroup `pnl_monthly`'s stored leaves into Elena's six rows using the mapping above.
- Reproduce **US** first (no known Sellerise defects — should tie closely): compare regrouped Sales,
  COGS, Ad Spend, Selling Fees, Operational Fees, Refunds, Reimbursements against Elena's US column
  (image 2: Sales 175,192; COGS 45,968; Ad 31,369; Selling 50,709; Operational 14,912; Refunds 9,617;
  Reimb 1,442 — January). Report per-row Δ.
- Then **UK**. Expect Selling Fees to diverge by ~the GMAKER-3 FBA gap. **Classify each Δ**:
  *expected (known Sellerise defect, with the cell + magnitude)* vs *unexplained (mapping error)*.
- Do the same spot-check for CA and AU where Elena's per-marketplace figures are available.

## Step 3 — Report, don't fix

Output `reference/data/pnl_dashboard_probe.md`:
- `pnl_monthly` schema + coverage.
- The verified bucket→row mapping (Elena's leaf names → your actual leaves), with unmatched leaves both
  directions flagged.
- The three collisions resolved with evidence (reimbursement/clawback sign & side; CA cog currency;
  Selling Fees defect exposure).
- Per-marketplace, per-row reproduction table with Δ, each Δ classified **expected-divergence** (named
  cause) or **unexplained** (must resolve before the dashboard ships that row).
- A plain list of expected divergences the dashboard will show vs Elena's sheet, with their one-line
  causes — this becomes the dashboard's "why doesn't this match my spreadsheet" answer.

## Guardrails

- Read-only. No schema change, no API, no UI, no writes.
- Do not "fix" a divergence that is a known Sellerise defect — the correct Amazon figure is what ships.
- An unexplained, material Δ is a **finding to resolve**, not a tolerance to widen. Report it; do not
  paper over it.
- Do not alter reconciliation math, buckets, or `pnl_monthly`.
- If `pnl_monthly` does NOT reproduce a marketplace's own reconcile report (independent of Elena's
  sheet), that's a stale-materialization bug — flag it loudly; the dashboard can't read a table that
  disagrees with the reports.

## Definition of done

- `pnl_monthly` schema, currency handling, and marketplace×month coverage documented.
- Bucket→row mapping verified against actual leaves; unmatched leaves flagged both directions.
- The three collisions resolved with evidence.
- Reproduction table per marketplace: US ties closely; every non-trivial Δ classified expected vs
  unexplained; no unexplained material Δ left undiagnosed.
- The "expected divergences vs Elena's sheet" list written — the dashboard's credibility answer.
- Confirmation that pnl_monthly agrees with the reconcile reports (not just with Elena's sheet).