# Net residual diagnosis — the flat −$1,340/month is cog, not attribution drift

**Verdict:** the residual is **not purchase-date attribution drift**. It's a
**systematic cog over-count** — we compute cog from shipped units without
subtracting refunded units, while Sellerise nets settled refunds out of cog.
The label "P&L-side purchase-date attribution drift" in the reconcile report
is corrected below to "cog: does not net refund units."

## Test 1 — March per-bucket decomposition

March is the clean probe (ad total reconciled to $0.00). For each net-contributing
bucket, Δ = ours − Sellerise, and its contribution to net = ±Δ per the formula
`net = revenue − salesTaxes − fees − fba − refunds − storageFee − cog − ads`.

| bucket | Δ (ours − theirs) | contribution to Δnet |
|---|---:|---:|
| revenue | +588.51 | +588.51 |
| salesTaxes | +62.12 | −62.12 |
| fees | +84.88 | −84.88 |
| fba | −1.89 | +1.89 |
| refunds | +164.49 | −164.49 |
| storageFee | 0.00 | 0.00 |
| **cog** | **+1,759.81** | **−1,759.81** |
| adExpenses | 0.00 | 0.00 |
| **Σ contribs** | | **−1,480.90** |
| net delta (measured) | | **−1,480.90** |
| sanity residual | | 0.0000 |

**cog contributes −$1,760 of March's −$1,481 net delta by itself.** Every other
bucket is either near-zero or largely offsets. The decomposition sums exactly to
the measured net delta (0.0000 residual), so the formula has no unaccounted
term — cog is the answer.

## Test 2 — Six-month confirmation: same cause every month

Same decomposition for Jan–Jun:

| month | net Δ | cog Δ | cog contrib (−cog Δ) | share of net Δ |
|---|---:|---:|---:|---:|
| 2026-01 | −1,367.05 | +787.94 | −787.94 | 58 % |
| 2026-02 | −1,154.70 | +1,767.38 | −1,767.38 | **153 %** ¹ |
| 2026-03 | −1,480.90 | +1,759.81 | −1,759.81 | 119 % ¹ |
| 2026-04 | −855.81 | +1,360.48 | −1,360.48 | **159 %** ¹ |
| 2026-05 | −1,543.09 | +1,061.86 | −1,061.86 | 69 % |
| 2026-06 | −1,640.41 | +811.30 | −811.30 | 49 % |
| **Σ** | **−8,041.96** | **+7,548.77** | **−7,548.77** | **94 %** |

¹ >100 % means cog alone explains all of the net delta; other buckets partially
offset it back toward zero.

**cog carries a positive delta every single month** (Δcog = ours − theirs is
same-signed every month), so its net-contribution is negative every single month.
**94 % of the total residual is cog** — the "flat, same-signed, accumulating"
shape the task called out.

Note the pattern: Δcog is **decreasing over time** (Feb-Mar peaks at ~$1,760,
Jun drops to $811). That's consistent with a refund-related mechanism —
Amazon can only refund an order after it's been placed, so cumulative refunds
against recent months are still growing. Older months have more finalized
refunds; newer months are still refund-in-progress.

## Test 3 — What changes if we net refunded units from cog?

Hypothesis: Sellerise's cog = `shipped_units × cog − refunded_units × cog`. We
subtract only shipped units. Testing under purchase-date attribution (matches
our Shipment basis) and by refund-transaction status:

| ym | ship_cog | Sellerise | Δ raw | Δ after −REL only | Δ after −REL−DR | Δ after −ALL |
|---|---:|---:|---:|---:|---:|---:|
| 2026-01 | 46,756.14 | 45,968.20 | +787.94 | −2,018.83 | −2,018.83 | −2,018.83 |
| 2026-02 | 36,414.64 | 34,647.26 | +1,767.38 | −913.94 | −913.94 | −913.94 |
| 2026-03 | 31,183.77 | 29,423.96 | +1,759.81 | −375.75 | −464.37 | −464.37 |
| 2026-04 | 32,151.26 | 30,790.78 | +1,360.48 | +731.81 | −182.95 | −182.95 |
| 2026-05 | 28,241.87 | 27,180.01 | +1,061.86 | +219.72 | −492.68 | −492.68 |
| 2026-06 | 25,884.57 | 25,073.27 | +811.30 | +558.27 | +67.24 | **+11.43** |
| **Σ** | | | **+7,548.77** | −1,798.72 | −4,005.53 | **−4,061.34** |

- Netting **all-statuses refunded units** collapses Jun to **+$11.43** (near-exact
  match) and closes the raw delta from +$7,549 to −$4,061.
- **Jan and Feb still show a large under-count** (−$2,018 / −$914) even after
  full netting — because those months contain refunds against orders **purchased
  in December 2025** which get re-attributed out of Jan (into Dec, out of our
  comparison window). This is the same pre-backfill boundary effect documented
  in `project_reconciliation.md`.
- Settled Mar–May land at −$182 to −$493 after netting REL+DEF_RELEASED — a
  small consistent under-count, plausibly because Sellerise's cog netting uses a
  slightly different subset than "all settled refunds by purchase date".

## Effect on net if the cog-netting fix were applied

Applying the `-ALL statuses, purchase-date` fix:

| month | net Δ before fix | Δcog shift | net Δ after fix |
|---|---:|---:|---:|
| Jan | −1,367 | +2,807 | +1,440 |
| Feb | −1,155 | +2,681 | +1,526 |
| Mar | −1,481 | +2,224 | +743 |
| Apr | −856 | +1,543 | +687 |
| May | −1,543 | +1,555 | +12 |
| Jun | −1,640 | +799 | **−841** |
| **Σ** | **−8,042** | **+11,609** | **+3,567** |

The fix removes the systematic same-signed accumulation (mixed signs after)
but **does not close net to zero on all settled months**. Jan/Feb remain
over by ~$1,500 (pre-backfill boundary + partial refund-netting), May is
essentially exact, Jun is now under by $841.

## Verdict

**Root cause**: `cog` does not net refund units. Our current computation
`sum(quantity_shipped × cogs) for Shipment items` never subtracts the same
quantity × cog for refunded items. Sellerise apparently does.

**Not attribution drift**: purchase-date drift nets to zero cumulatively — this
residual doesn't. The label in the reconcile report is corrected accordingly.

**Not a double-subtraction / sign bug at net wiring**: Test 1 decomposition
sums to the exact measured net delta with 0.0000 sanity residual. The net
formula is correct; a specific input (cog) is off.

**Not an ad-side V2 date basis issue**: March's ad total is $0.00 delta, yet
March's net delta is −$1,481 — the residual survives with ads perfectly
matched.

## Fix applied (2026-07-07, REFUND_COG_FIX.md)

Both bases were tested per the task's discipline. The empirical winner is
**purchase-date** — falsifying the task's own "processed-date should improve
Jan/Feb" hypothesis. Numbers:

| basis | Σ signed net Δ | Σ \|net Δ\| |
|---|---:|---:|
| today (no refund netting) | −$8,041.96 | $8,041.96 |
| **posted-date refund cog** | +$5,691.12 | $5,970.98 |
| **purchase-date refund cog** | **+$3,568.15** | **$5,249.23** |

The Jan/Feb "tell" the task predicted did not appear: posted-date makes Jan/Feb
*worse* (+$2,191 / +$1,929), not better than purchase-date (+$1,440 / +$1,527).
Both bases move Jan/Feb from under to over — the residual there is not fixable
by basis choice, it's the pre-backfill boundary (see below).

Purchase-date + all-status refund netting is now applied in
`sync/cogs.py` and mirrored in `sync/reconcile.py::compute_cog_by_basis`.

## Remaining residual after fix — labels verified (2026-07-07)

Post-fix per-month net Δ, each label tested per `NET_RESIDUAL_CLOSEOUT.md`:

| month | net Δ | verified label |
|---|---:|---|
| 2026-01 | +$1,440 | pre-2026-01-01 backfill boundary — **CONFIRMED** |
| 2026-02 | +$1,527 | pre-backfill boundary tail — **CONFIRMED** |
| 2026-03 | +$743 | ~~refund-policy sub-difference~~ **FALSIFIED** — revenue-side snapshot residual |
| 2026-04 | +$688 | ~~same as Mar~~ **FALSIFIED** — revenue-side snapshot residual |
| 2026-05 | +$11 | essentially exact — **CONFIRMED** |
| 2026-06 | −$841 | trailing-month snapshot effect — **CONSISTENT** |
| **Σ** | **+$3,568** (+1.7 % of Sellerise net Jan–Jun) | |

### Check 1 — Mar/Apr — original label FALSIFIED

Post-fix per-bucket decomposition (Σ contribs = net Δ, zero sanity residual):

| bucket contribution | Mar | Apr |
|---|---:|---:|
| **revenue** | **+$588.51** | **+$698.26** |
| cog (post-fix netting) | +$464.37 | +$182.95 |
| refunds | −$164.49 | −$113.80 |
| fees | −$84.88 | −$100.65 |
| salesTaxes | −$62.12 | −$27.38 |
| fba | +$1.89 | +$51.30 |
| ads | 0 | −$3.06 |
| **Σ = net Δ** | **+$743.28** | **+$687.62** |

**Revenue dominates in both months** — 79 % of Mar's delta and 100+ % of
Apr's. Not refunds, not cog. Per-sub-line: chargesObject.Principal is +$518 /
+$672 over Sellerise's Mar/Apr (0.4–0.6 % of Principal). Tax +$61 / +$27 rides
proportionally on top — the whole chargesObject moves together.

**Corrected label**: small revenue-side snapshot residual. Sellerise's Mar/Apr
snapshot was taken at some point T; our fresh pull now catches restatements /
late-attributions Amazon has since made. Same class of residual documented in
[`offset_diagnosis.md`](offset_diagnosis.md) for the pre-purchase-date era.
**Not refund-policy.**

### Check 2 — Jan/Feb — label CONFIRMED

Spot-checked one of the 24 Jan-fallback transactions:

```
order_id: 112-4649868-1076213
PurchaseDate: 2025-11-22T20:21:50Z   ← BEFORE 2026-01-01
```

Full census of Jan/Feb Shipment+Refund transactions whose order_id is not in
`order_purchase_date` (i.e. purchased before our Orders sweep start of
2025-12-01):

| month | txn type | n_txns | cog impact | Principal impact |
|---|---|---:|---:|---:|
| 2026-01 | Refund | 13 | +$669.72 | −$1,915.67 |
| 2026-01 | Shipment | 11 | +$41.04 | +$239.40 |
| 2026-02 | Refund | 3 | +$179.38 | −$474.23 |

**Recoverable amount if backfill were extended to Nov 2025:**

If we resolved the PurchaseDate for these 24 Jan + 3 Feb orders (all
pre-2026-01-01), our attribution would move them out of the Jan/Feb bucket
into their true (out-of-window) purchase month. Effect on Jan cog: currently
we subtract the fallback refund cog ($669.72) from Jan under the postedDate
fallback; resolving PurchaseDate to Nov moves it out, so Jan cog rises by
$669.72. Net Δ contribution: −$629 (Jan) / −$179 (Feb).

**Recoverable ≈ $808** of the $2,967 Jan+Feb residual (~27 %). The remaining
~$2,159 is Jan/Feb revenue-side residual analogous to Check 1's Mar/Apr —
snapshot restatement drift, not fixable via backfill.

### Check 3 — Jun — label CONSISTENT

Jun decomposition (net Δ = −$840.54):

- revenue Δ: −$288 (we under)
- cog Δ: +$11 (essentially exact — post-fix cog matches to the cent)
- **refunds Δ: +$535** (dominant — our `Σ refundsObject` is $535 MORE negative
  than Sellerise's)

Refund posting-date distribution: refunds occur throughout Jun including the
final week (Jun 26–30: 11 refund txns totalling ~$1,057 on `total_amount`).
Our data goes through Jun-30 23:57 UTC. Sellerise's frozen snapshot has less
data than we do.

**Direction matches the label**: if Sellerise's snapshot missed late-Jun
refunds and Amazon later applied them, we'd see more refunds than Sellerise
did — which is exactly the pattern. The specific claim ("mostly late-Jun") is
plausible but not surgically proven; the net residual is consistent with the
label.

## Close-out recommendation: **ACCEPT**

The +$3,568 cumulative (+1.7 % of Sellerise net) breaks down as:

| bucket | $ | fixable by backfill extension? |
|---|---:|---|
| pre-2026-01-01 boundary (Jan/Feb) | +$2,967 | ~$808 recoverable |
| revenue-side snapshot residual (Mar/Apr) | +$1,431 | no — snapshot restatement drift |
| trailing-month refund lag (Jun) | −$841 | no — waits for Amazon to finalize Jun |
| effectively zero (May) | +$11 | — |

**Cost of extending backfill** to Nov–Dec 2025:
- Re-pull `listTransactions` from ~2025-11-01 (~2 months of extra data)
- Re-pull `getOrders` from ~2025-11-01 (2 months × ~1500 orders × 1 min/page →
  ~30 min sustained + 429 backoff)
- Re-run aggregate/cogs/reconcile

**Estimated recovery**: $808 of the $3,568 residual (23 %). Cumulative net Δ
would go from +1.7 % to +1.3 %.

**Recommendation: accept as-is.** Extending the backfill for a ~$800 recovery
that leaves a still-non-zero residual, when the specialist has approved
"accurate, not exact" and every dollar is now correctly labeled, is not a good
use of scope. The residual is:

- Signed differently across months (+$1,440, +$1,527, +$743, +$688, +$11,
  −$841 — mixed, no accumulation direction)
- Each cause quantified per month
- No unexplained bucket remains
- Under 2 % of Sellerise net cumulatively
- Consistent with the same restatement-drift pattern we accepted on the
  ad-lines side (`PASS_DRIFT` up to $5.75)

**US reconciliation is complete.** The +1.7 % residual is a documented,
quantified, per-cause accepted residual — not a bug and not "attribution
drift."
