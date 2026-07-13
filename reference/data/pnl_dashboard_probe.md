# pnl_monthly probe — schema, bucket→P&L-row mapping, and expected divergences vs Elena's sheet

Read-only probe for the v1 P&L dashboard (month-as-column grid, rows = P&L line items). No schema
change, no API, no UI, no writes. Confirms: (1) `pnl_monthly`'s real schema/coverage, (2) that its
stored buckets regroup into Elena's six rows, (3) where they will *not* tie — because the dashboard
shows the correct Amazon figure, not Sellerise's.

**Headline for the build:**
- `pnl_monthly` is the right source for six of seven rows. **Ad Spend is NOT in `pnl_monthly`** — it
  must come from `ad_spend_daily` (matches Elena to $0.60; see §4).
- `pnl_monthly` agrees with the reconcile reports to the cent (§2) — no stale-materialization bug.
- Every US row reproduces Elena within a **named** cause. There are no unexplained material Δ.

---

## 1. Schema + coverage

`pnl_monthly` columns (migrations `feccfae1778b`, PK widened by `b2c3d4e5f6a7`):

| column | type | notes |
|---|---|---|
| marketplace_id | text | literal Amazon id |
| year_month | char(7) | e.g. `2026-01` |
| line_key | text | leaf id, e.g. `Principal`, `ServiceFee.FBAInboundTransportationFee` |
| line_label | text | human label |
| bucket | text | one of 8 (below) |
| amount | numeric(18,4) | signed; revenue +, costs − |
| currency | text | **per-row** (see §5) |
| computed_at | timestamptz | materialization time |

**PK = (marketplace_id, year_month, bucket, line_key)** — one row per marketplace/month/bucket/leaf.
`bucket` is in the PK because Sellerise reuses sub-line names across buckets (e.g. `Commission` in both
`feesObject` and `refundsObject`). **`net` is NOT stored — it is derived** (the reconcile computes it
in memory; the dashboard must sum rows).

**Coverage** (settled months = Jan–Jun 2026; Dec 2025 is a partial buffer, Jul 2026 in-progress):

| mp | months present | currency | computed_at |
|---|---|---|---|
| US | 8 (2025-12 … 2026-07) | USD | 2026-07-13* |
| CA | 7 (2025-12 … 2026-06) | CAD + USD | 2026-07-10 |
| UK | 7 (2025-12 … 2026-06) | GBP | 2026-07-10 |
| AU | 7 (2025-12 … 2026-06) | AUD + USD | 2026-07-10 |

\* US shows an extra month + fresher `computed_at` only because the cron test re-ran US today; values
unchanged. All four marketplaces × all six settled months are present.

**The 8 buckets:** `chargesObject` (sales-side), `cog`, `feesObject` (referral/commission + chargebacks),
`fbaObject` (FBA fulfilment fees), `storageFee`, `expenses` (service/adjustment/reimbursement leaves —
**excluded from the reconcile's net**), `passthrough` (facilitator tax/VAT, reserves, ProductAds
settlement, fund transfers — net-neutral), `refundsObject`.

---

## 2. `pnl_monthly` agrees with the reconcile reports (integrity gate)

The dashboard can't read a table that disagrees with the reports. It doesn't — `pnl_monthly.amount`
equals each report's **"after (ours)"** column to the cent:

| mp | cell (2026-01) | pnl_monthly | report "after (ours)" |
|---|---|---|---|
| US | chargesObject.Principal | 166,439.37 | 166,439.37 |
| US | cog | 43,949.37 | 43,949.37 |
| CA | chargesObject.Principal | 9,584.03 | 9,584.03 |
| CA | cog | 1,445.51 | 1,445.51 |
| UK | chargesObject.Principal | 11,349.95 | 11,349.95 |
| UK | cog | 3,388.38 | 3,388.38 |

The report's **"Sellerise"** column = Elena's sheet (proof: US cog Sellerise = 45,968.20 = Elena's
COGS 45,968). So "ours vs Elena" per row is exactly the reconcile's documented ours-vs-Sellerise Δ.

---

## 3. Bucket → Elena-row mapping (verified against actual leaves)

| Elena row | pnl_monthly source | notes |
|---|---|---|
| **Sales** | `chargesObject` (all leaves) | Principal, Tax, Promotion(−), Shipping±, GiftWrap±. Ties to Elena's `revenue`. |
| **COGS** | `cog` | one leaf. Refund-netted, purchase-date basis. |
| **Ad Spend** | **`ad_spend_daily`** (not pnl_monthly) | see §4 — critical. |
| **Selling Fees** | `feesObject` + `fbaObject` | referral/commission + FBA. Elena also folds facilitator tax in — §6a. |
| **Operational Fees** | `storageFee` + `expenses` (non-reimbursement leaves) | ServiceFee.*, Adjustment.*, Removal/Retrocharge, `FBAReversedReimbursement` (money out). |
| **Refunds** | `refundsObject` (all leaves) | |
| **Reimbursements** | `expenses.FBAInventoryReimbursement.FBAInventoryReimbursement` (money in) | §6b — direction split. |

**Unmatched, both directions:**
- *Elena leaves with no clean 1:1 counterpart:* Sellerise names ~17 `expenses` leaves ("Inbound
  Transportation Fee", "Premium Services Fee", "AmazonFees", "StorageRenewalBilling", "DisposalComplete",
  "RemovalComplete", "COMPENSATED_CLAWBACK", "MISSING_FROM_INBOUND", "WAREHOUSE_DAMAGE", "WAREHOUSE_LOST",
  "REVERSAL_REIMBURSEMENT", "FREE_REPLACEMENT_REFUND_ITEMS", …). Ours carries the same economics under
  different names (`ServiceFee.FBAInboundTransportationFee`, `ServiceFee.PaidServicesFee`,
  `Adjustment.AmazonFees`, `ServiceFee.FBALongTermStorageFee`, …) **and at coarser granularity for
  reimbursements** (2 direction-split leaves vs Sellerise's ~7 named ones — §6b). Row totals reconcile;
  leaf-for-leaf does not.
- *pnl_monthly leaves Elena's list omits:* the entire `passthrough` bucket (facilitator tax/VAT,
  `Adjustment.Reserve*`, `Transfer.FundTransfer`, `ProductAdsPayment.*`, `Shipment.Promo`). These are
  net-neutral passthroughs; none is a P&L row. **`Transfer.FundTransfer` (US Jan +100,088)** is a
  settlement cash movement — must never enter a P&L row.

---

## 4. Ad Spend is not in `pnl_monthly` — use `ad_spend_daily`

There is no `adExpenses` bucket in `pnl_monthly`. The only ad line inside it is
`passthrough.ProductAdsPayment.AdvertisingFee` — the **settlement** ad charge — which is close but not
Elena's figure. The correct source is `ad_spend_daily` (Ads-API campaign spend, what the reconcile
already uses for net):

| source (US 2026-01) | value | Δ vs Elena |
|---|---|---|
| `ad_spend_daily` (Ads API) | 31,368.66 | **−0.60** |
| Elena `adExpenses` (Sellerise) | 31,369.26 | — |
| `passthrough.ProductAdsPayment.AdvertisingFee` (settlement) | −31,317.11 | −52.15 |

**Build note:** the dashboard's Ad Spend row joins `ad_spend_daily` (sum `total_cost` by
marketplace/month), NOT `pnl_monthly`. `ad_spend_daily` covers all four marketplaces, Jan–Jun.

---

## 5. Currency (CA/AU cog is USD; the rest native)

`currency` is per-row. Sales-side buckets are native (US=USD, CA=CAD, UK=GBP, AU=AUD), but **CA and AU
store `cog` in USD** (the `MARKETPLACE_COG_SOURCE_OVERRIDE` — a USD cog is compared to Sellerise's USD
`cog` field, while sales are CAD/AUD):

| mp | chargesObject | cog | others |
|---|---|---|---|
| CA | CAD | **USD** | CAD |
| AU | AUD | **USD** | AUD |

**Native single-marketplace view (CA/AU): the COGS row (USD) sits next to Sales (CAD/AUD) — not
coherent without handling.** Two options: convert cog USD→native for display (CA: ÷0.71, AU: ÷0.69 at
Elena's book rates), or show it natively with a "COGS in USD" note. Recommend converting for display so
the column is internally consistent in one currency.

**"All → USD" view:** convert native→USD at Elena's book rates (GBP×1.34, CAD×0.71, AUD×0.69), but
**CA/AU cog is already USD — do not convert it** (double-conversion trap; this is exactly the AU bug the
project fought). Book rates belong in config, labelled as Elena's book rates.

---

## 6. The three collisions, resolved with evidence

### 6a. Selling Fees carries facilitator tax (Elena) + known Sellerise defects — expected divergence
Elena's "Selling Fees" folds the marketplace facilitator tax / VAT (`salesTaxes`) into the row. Proven
across all three Sellerise markets (2026-01):

| mp | fees+fba | + salesTaxes | = Elena's Selling |
|---|---|---|---|
| US | 41,581.38 | 9,122.00 | 50,703 (Elena 50,709) |
| CA | 2,793.50 | 890.66 | 3,684.16 |
| UK | 2,738.29 | 2,127.82 | 4,866.11 |

Facilitator tax is money Amazon collects from the buyer and remits — a **passthrough, net-neutral to the
seller**. The dashboard's Selling Fees = referral + FBA only, so it reads **lower than Elena by the
`salesTaxes` amount**. That is correct, not a bug. Separately, **UK Selling Fees also runs higher than
Sellerise's own fee figure by the GMAKER-3 FBA gap** (UK ours fees+fba 2,929.77 vs Sellerise 2,738.29,
**+191.48** — Sellerise understates GMAKER-3's FBA fee; `pnl_monthly` holds the correct Amazon charge).

### 6b. Reimbursement vs reversal — our leaves split by direction (preferred outcome)
`pnl_monthly` distinguishes the two directions Elena's sheet double-lists:
`expenses.FBAInventoryReimbursement.FBAInventoryReimbursement` (money **in**) and
`…FBAReversedReimbursement` (money **out**). So map **money-in → Reimbursements (positive)**, **money-out
→ Operational Fees (negative)**. This *resolves* Elena's double-listing of `reversal reimbursement`
(under both Operational and Reimbursements) rather than overriding it — each of her two placements
captures one real direction. **Report to Elena for confirmation.**

Caveat (granularity): ours carries 2 direction-split leaves; Sellerise names ~7
(`REVERSAL_REIMBURSEMENT`, `MISSING_FROM_INBOUND`, `WAREHOUSE_DAMAGE`, `WAREHOUSE_LOST`,
`COMPENSATED_CLAWBACK`, `MISSING_FROM_INBOUND_CLAWBACK`, `FREE_REPLACEMENT_REFUND_ITEMS`). So the
Operational-vs-Reimbursements **split** differs, but the **combined net ties** (US Jan: ours −13,762.95
vs Elena −13,470.00, Δ −292.95). Reimbursements (in) and Operational clawbacks (out) do not double-count.

### 6c. CA COGS currency — see §5
`pnl_monthly` stores CA cog in **USD** (1,445.51) next to CAD sales. Confirmed; needs the §5 display
handling in the native CA view.

---

## 7. Reproduction — US 2026-01 (ours = dashboard, Elena = Sellerise), every Δ classified

| row | ours | Elena | Δ | classification |
|---|---|---|---|---|
| Sales | 174,304.82 | 175,191.94 | −887.12 | **expected** — restatement drift (per-cell in report: Principal −698, Tax −80, Shipping −78, Promo −22 …) |
| COGS | 43,949.37 | 45,968.20 | −2,018.83 | **expected** — US cog is refund-netted, purchase-date basis; part of the documented US +1.7% residual |
| Ad Spend | 31,368.66 | 31,369.26 | −0.60 | **ties** — from `ad_spend_daily` |
| Selling Fees | 41,335.98 | 50,703.38 | −9,367.40 | **expected by design** — Elena folds `salesTaxes` (9,122, passthrough) in; residual real fee drift only −245 |
| Operational Fees | 16,550.25 | 14,912.08 | +1,638.17 | **expected (structural)** — reimbursement-leaf granularity; see combined ↓ |
| Refunds | 9,644.40 | 9,617.42 | +26.98 | **expected** — small restatement drift |
| Reimbursements | 2,787.30 | 1,442.08 | +1,345.22 | **expected (structural)** — our money-in leaf aggregates more Sellerise leaves |
| *Operational + Reimb (net)* | −13,762.95 | −13,470.00 | −292.95 | the split diverges by granularity; **combined ties within $293** |

**No unexplained material Δ.** US ties closely once the two structural items (salesTaxes fold-in,
reimbursement granularity) are named.

**CA / UK spotlight (2026-01):**
- CA Selling ours 2,844.99 vs Elena 3,684.16 (Δ −839, = CA `salesTaxes` 890.66 fold-in less small fee
  drift). CA COGS ours 1,445.51 vs Elena 1,587.21 (Δ −141.70, the documented CA cog residual; **USD**).
- UK Selling ours 2,929.77 vs Elena 4,866.11 (Δ −1,936, = UK VAT `salesTaxes` 2,127.82 fold-in, partly
  offset by the +191 GMAKER-3 gap). UK COGS ours 3,388.38 vs Elena 3,145.54 (**Δ +242.84 — ours HIGHER**;
  UK per-SKU costs tie to invoice, Sellerise understates ABDB/MBUKB1). Correct Amazon figure ships.

**AU:** reconciles against **Sellerboard, not Sellerise** — there is no Elena/Sellerise column for AU.
The dashboard reads AU rows from `pnl_monthly` (AUD, cog USD per §5); its comparison target, if any, is
the Sellerboard reconcile (`au_sellerboard_reconcile.md`), not Elena's sheet.

---

## 8. Expected divergences the dashboard WILL show vs Elena's sheet (the "why doesn't this match my
spreadsheet" answer)

1. **COGS lower than Elena** (US −2,019/mo, CA −142) — our cog is refund-netted on a purchase-date
   basis (the reconciled Amazon figure). *(UK COGS is instead **higher** — see #4.)*
2. **Selling Fees lower than Elena by the sales/facilitator tax** — Elena folds `salesTaxes`/VAT into
   Selling Fees; the dashboard treats facilitator tax as passthrough (net-neutral), so Selling Fees =
   referral + FBA only. (US ≈ −9,122/mo; CA ≈ −891; UK ≈ −2,128.)
3. **Ad Spend from `ad_spend_daily`** — matches Elena to ~$1; the settlement ad line in `pnl_monthly`
   would be ~$52 lower and is not used.
4. **UK Selling Fees & COGS higher than Elena** — Sellerise understates GMAKER-3's FBA fee (+191/mo) and
   UK per-SKU costs; `pnl_monthly` holds the invoice-correct Amazon figures.
5. **Reimbursements / Operational split differs** — direction-split (money-in vs money-out) instead of
   Sellerise's ~7 named leaves; the two rows' **combined** total matches, individual rows shift by
   ~$1.3k (US Jan). Pending Elena's confirmation of the reversal-reimbursement placement (§6b).
6. **CA/AU COGS shown in USD** unless converted for display (§5); small restatement drift on Sales and
   Refunds every month (sub-1%).

Items 1–4 and 6 are settled (correct Amazon figure ships). **Item 5 (reversal-reimbursement placement)
is the one PROVISIONAL point pending Elena's confirmation** before the Operational/Reimbursements rows
ship.
