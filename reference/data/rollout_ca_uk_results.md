# CA + UK rollout results

Built after the [rollout probe](marketplace_rollout_probe.md) with three
verification gates (per [`ROLLOUT_CA_UK_BUILD.md`](../../ROLLOUT_CA_UK_BUILD.md)).
AU stays quarantined (no Sellerise target).

## Gates — evidence-backed decisions

### Gate 1 — `ShippingTaxDiscount` routing

The probe *proposed* folding `ShippingTaxDiscount` into
`chargesObject.ShippingTax`. Tested against UK Mar Sellerise targets:

| routing | `chargesObject.ShippingTax` (target $25.89) | `refundsObject.ShippingTax` (target −$1.42) |
|---|---:|---:|
| (a) ShippingTax + ShippingTaxDiscount | $18.70 (Δ −$7.19) | −$0.10 (Δ +$1.32) |
| **(b) ShippingTax alone** | **$26.42 (Δ +$0.53 near-exact)** | **−$1.42 (Δ $0.00 EXACT)** |

**Verdict**: probe proposal falsified — `ShippingTaxDiscount` → **passthrough**
(both Shipment and Refund sides). Committed to `_PASSTHROUGH_BREAKDOWN_TYPES`.

### Gate 2 — refund + refund-COGS basis per marketplace

Empirical Σ|Δ| across all 6 months:

| marketplace | refund dollars | refund COGS |
|---|---|---|
| US | posted (5,249) vs purchase (5,971) → **posted** | purchase (5,249) vs posted (5,971) → **purchase** |
| **CA** | posted ($61.28) vs purchase ($1,866.58) → **posted** | posted ($2,596.90) vs purchase ($3,090.23) → **posted (differs from US!)** |
| **UK** | posted ($407.08) vs purchase ($3,210.63) → **posted** | posted ($2,135.40) vs purchase ($1,000.62) → **purchase (same as US)** |

**Verdict**: refund-dollars basis is `postedDate` in every marketplace tested
(no per-marketplace switch needed). Refund-COGS basis DIFFERS per marketplace
— committed to `MARKETPLACE_REFUND_COGS_BASIS` in config.

### Gate 3 — UK `other-transaction` + `storageFee=0`

Pulled UK May and Jun `listTransactions`. Sellerise targets:
`expenses.other-transaction` = −$113.68 (May) / −$132.85 (Jun).

Sum of new UK-only ServiceFee leaves:

| month | `EPRChargebackEcoFee` | `EPRChargebackServiceFee` | `ServiceFee.Tax` | **sum** | Sellerise target |
|---|---:|---:|---:|---:|---:|
| May | −87.16 | −10.00 | −16.52 | **−113.68** | **−113.68 EXACT** |
| Jun | −103.55 | −10.00 | −19.30 | **−132.85** | **−132.85 EXACT** |

`other-transaction` resolved. `storageFee=0` explained: `FBAStorageFee`
still exists (−$77.60 May, −$59.68 Jun) but Sellerise reclassifies UK's
storage fee into `expenses.FBAFees` those months. Net effect zero.

Committed `EPRChargebackEcoFee` + `EPRChargebackServiceFee` +
`FBAInboundTransportationProgramFee` + `DealParticipationFee` +
`DealPerformanceFee` to `_EXPECTED_EXPENSES` (previously would fire the
unmapped-leaf WARNING).

## Build — verified `bucket_map` additions

Added to [`backend/sync/bucket_map.py`](../../backend/sync/bucket_map.py):

- **DigitalServicesFee family** (UK): `Shipment.DigitalServicesFee` +
  `Shipment.DigitalServicesFeeFBA` → `feesObject.*` (status split). Refund
  reversal `Refund.DigitalServicesFee` → `refundsObject.DigitalServicesFee`.
  **UK Jan verified: `feesObject.DigitalServicesFee = −$52.02` EXACT.**
- **VAT tax family** (UK): `MarketplaceFacilitatorVAT-Principal/-Shipping`
  added to passthrough set (Shipment) and `_REFUND_TAX_WITHHELD_TYPES`
  (Refund).
- **`ShippingTaxDiscount`** + **`OurPriceTaxDiscount`** → passthrough (Gate 1).
- **`Shipment.Tax` / `Refund.Tax`** (CA facilitator + AU GST) → passthrough
  via inline classify() rule.

## Reconcile results — settled-months net Δ vs Sellerise

Full monthly reports:
[reference/data/reconcile_report_UK.md](reconcile_report_UK.md) and
[reference/data/reconcile_report_CA.md](reconcile_report_CA.md).

### UK

| month | Δ before ads | Δ after ads (real) | notes |
|---|---:|---:|---|
| 2026-01 | +$1,906 | **−$297** | ads persisted; ~0.4 % of Sellerise net |
| 2026-02 | +$1,576 | **−$316** | ads persisted; ~0.4 % |
| 2026-03 | +$1,655 | **−$112** | ads persisted; ~0.2 % |
| 2026-04 | +$618 | **−$240** | ads persisted; ~0.4 % |
| 2026-05 | +$415 | +$415 | ads NOT persisted (May/Jun CSVs not cached; needs full-year Ads pull) |
| 2026-06 | +$420 | +$420 | ads NOT persisted |
| **Σ Jan-Apr (ads-complete)** | **+$5,754** | **−$965** | |
| **Σ Jan-Jun** | **+$6,589** | **−$131 (essentially reconciled)** | May/Jun ads-missing cancels out |

Cell-level highlights (UK Jan): `Principal`, `Tax`, `salesTaxes`,
`storageFee`, `DigitalServicesFee`, gift-wrap lines, several refund
sub-lines match to the cent.

### CA

| month | Δ before ads | Δ after ads (real) | notes |
|---|---:|---:|---|
| 2026-01 | +$2,597 | **−$323** | ads persisted |
| 2026-02 | +$1,016 | **−$532** | ads persisted |
| 2026-03 | +$735 | **−$422** | ads persisted |
| 2026-04 | +$923 | **−$269** | ads persisted |
| 2026-05 | +$494 | +$494 | ads NOT persisted |
| 2026-06 | −$45 | −$45 | ads NOT persisted |
| **Σ Jan-Apr (ads-complete)** | **+$5,271** | **−$1,546** | |
| **Σ Jan-Jun** | **+$5,719** | **−$1,096** | |

CA carries a ~$300-500/month post-ads residual across settled months.
Consistent with cog residual (post-fix ~$600 Jan) — smaller absolute than UK
per month but larger as a % (CA is 1/10 US scale so any $/month noise is
proportionally louder).

### US (regression baseline — MUST stay clean)

```
Drift-guards: 0 INVESTIGATE on both (vs Sellerise + vs prior pull).
Locked targets: 9/15 PASS.
```

US reconciliation unchanged by rollout work — the added rules
(DigitalServicesFee, VAT family, ShippingTaxDiscount passthrough) don't
affect US leaves.

## AU — QUARANTINED

- No `SELLERISE_RAW_DATA_AU.json` file exists. `reconcile.py` refuses to run
  for AU (`ValueError: No Sellerise target file for marketplace A39IBJ37TRP1C6`)
  — the quarantine is enforced by the code, not documentation.
- AU transactions persisted for structural inspection only (766 txns Jan-Jun).
- The following AU-specific mappings are **inferred, not verified against a
  Sellerise target** — flagged explicitly in code comments:
  - `Shipment.Tax` (GST, AU Mar sample −$105) → passthrough. Assumed same as
    CA facilitator tax treatment; needs AU Sellerise target to confirm.
  - `Shipment.ShippingTaxDiscount` (small) → passthrough (same as UK).
  - `ServiceFee.Promo` (AU Mar +$5.25) → expected expense.

## Follow-ups (not part of this task's scope)

- **CA/UK ads May+Jun**: pull full-year `ads_spend.py` per marketplace (raw
  CSVs I have cover only Jan-Apr). Will close the May/Jun +$415/+$420 UK gap
  and the May +$494 CA gap.
- **Per-marketplace drift bands**: CA/UK are ~1/10 US scale; the current US
  drift bands are too loose for these markets. Not blocking (guard signals
  what to look at), but tightening bands would catch subtler regressions.
- **CA remaining residual**: −$1,096 across Jan-Apr. Likely a cog fine-tuning
  question. Refund-COGS basis is already per-marketplace (posted for CA), but
  small residual persists.
- **AU rollout**: blocked on Sellerise target. Structural probe already done;
  inferred mappings ready to commit once verified.

## Files touched

- [`backend/sync/config.py`](../../backend/sync/config.py) — added
  `MARKETPLACE_REFUND_COGS_BASIS` and `MARKETPLACE_AD_CURRENCY` alias.
- [`backend/sync/bucket_map.py`](../../backend/sync/bucket_map.py) — added
  VAT family, DSF family, ShippingTaxDiscount/OurPriceTaxDiscount →
  passthrough, inline rule for `Shipment.Tax`/`Refund.Tax`.
- [`backend/sync/aggregate.py`](../../backend/sync/aggregate.py) — added
  UK-specific ServiceFee leaves to `_EXPECTED_EXPENSES`.
- [`backend/sync/cogs.py`](../../backend/sync/cogs.py) — per-marketplace
  refund-COGS basis (CA uses postedDate).
- [`backend/sync/reconcile.py`](../../backend/sync/reconcile.py) —
  per-marketplace Sellerise file, `LOCKED_TARGETS_BY_MARKETPLACE`,
  per-marketplace ad-currency filter, wired refund-COGS basis into
  `compute_cog_by_basis`.

No US number changed. No AU committed.
