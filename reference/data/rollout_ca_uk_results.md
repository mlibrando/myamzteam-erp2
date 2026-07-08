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
| 2026-01 | +$1,906 | **−$297** | ~0.4 % of Sellerise net |
| 2026-02 | +$1,576 | **−$316** | ~0.4 % |
| 2026-03 | +$1,655 | **−$112** | ~0.2 % |
| 2026-04 | +$618 | **−$240** | ~0.4 % |
| 2026-05 | +$415 | **−$296** | Ads landed (£711.24 EXACT vs Sellerise) |
| 2026-06 | +$420 | **−$332** | Trailing DEFERRED; Ads landed (£751.57 EXACT) |
| **Σ Jan-Apr (ads-complete)** | **+$5,754** | **−$965** | all same-signed negative |
| **Σ Jan-Jun** | **+$6,589** | **−$1,594** | **NOT clean drift** — see UK diagnosis below |

**UK is NOT reconciling cleanly** — the earlier "UK done, small mixed-sign
drift" description was wrong. See UK residual diagnosis for the
per-bucket decomposition.

## UK residual diagnosis (`UK_RESIDUAL_DIAGNOSIS.md`)

UK's Σ Jan-Jun net Δ of **−$1,594 (−13.4 % of Sellerise net)** decomposes to
two systematic same-signed drivers (91 % of the residual):

| bucket | Σ Jan-Jun Δ | contribution to Σ Δnet | signature |
|---|---:|---:|---|
| `cog` | +$1,001 | **−$1,001 (63 %)** | positive every month, ours HIGHER |
| `fbaObject` (FBAPerUnit + FBAFees) | −$458 | **−$458 (29 %)** | negative every month, ours BOOKS MORE FBA |
| feesObject Commission↔ReferralFee split | net −$118 | −$118 | Sellerise-side split, cancels except Jan |
| refundsObject.Tax Withheld | −$108 | −$108 | mostly Jan (−$64) / Feb (−$33) DEFERRED lag |
| refundsObject.Principal | +$135 | +$135 | mostly Jan; small refund attribution drift |
| chargesObject.Promotion | +$63 | +$63 | small drift, Sellerise-side rounding |
| unaccounted small drift | | −$106 | mixed-sign under ~$20/cell |

### cog: per-SKU workbook value drift (fix = workbook data update)

- **UK cog is NOT US×N mechanically-derived** (unlike the CA bug this
  work chased). Per-ASIN ratios across UK vs US range 1.006–1.590 with
  most 1.01–1.05 — that's independently-entered per-SKU costs, not a
  fixed-multiplier bug. The CA writeup's "UK uses ≈US-parity cog"
  claim was based on ONE SKU (GMAKER-3 = 1.006); reality is more mixed.
- Per-unit cog gap: **ours $16.29–29.74/u vs Sellerise's $15.12–28.16/u**
  → +$0.17–3.01/u × units → +$29–$244/mo Δ, same-signed positive every
  month.
- **Ridge-anchored leave-one-out CV proves a stable per-SKU structure
  exists**: LOO-CV Σ|Δ| drops from $1,001 (baseline) to **$207–256**
  with per-SKU adjustments — meaning if UK sheet per-SKU cog values
  were tightened by ~5–15 % per SKU, the residual would collapse to
  ~$40/month mixed-sign (US/CA-post-fix scale).
- **No pipeline fix.** The workbook is the source of truth for per-SKU
  cost. This is a data-governance action (user updates UK sheet with
  more accurate per-unit costs), same fallback documented for CA when
  real per-SKU sourcing costs land.
- One CA-style structural note: UK has a **duplicate SKU listing**
  `B5-FUC0-5AKB` (71 units Jan–Apr) mapping to ASIN B088TWCGKL (same
  ASIN as `87-B4TQ-CWM8` which is in the workbook at £6.31). Sellerise
  aggregates by ASIN so it already includes this SKU's cost; ours drops
  it via the SKU-key join. Adding it would make our cog even higher,
  which is the wrong direction — it doesn't fix the residual and would
  amplify it by ~$448 across those months.

### fbaObject: Amazon post-snapshot restatement drift

- Raw sp_breakdowns UK Shipment FBA rate: **$3.53–3.86/unit** (stable
  across 6 months). Sellerise's implied rate: **~$3.24/unit** (~10 %
  lower). Same-signed −$60–$135/mo Δ.
- Attribution basis tested: purchase (Σ|Δ|=$458) beats posted ($504),
  confirms current config. Not attribution.
- No refund-side FBA breakdowns; no mapping leak.
- Signature (stable per-unit rate delta of ~10 %) is the classic
  restatement-drift fingerprint: Amazon revised UK FBA rates upward
  after Sellerise's snapshot. Not a pipeline mechanism.

### Bands: tightened so the residual doesn't stay silent

The earlier "0 INVESTIGATE on both guards" at −13.4 % net was the exact
monitoring failure the CA closeout task warned against — the band
absorbing the residual. UK bands were tightened to POST-FIX-expected
sizes (cog 500→100, fbaObject.FBAPerUnitFulfillmentFee 250→50,
Commission 300→200, refundsObject.Principal 250→200, Tax Withheld
150→100, FBAFees 50→25). At the current unresolved state UK reports:
- **9 INVESTIGATE cells vs Sellerise**: 4 cog (Jan/Feb/Apr/May) + 5
  fbaObject.FBAPerUnitFulfillmentFee (Jan–May). Jun stays trailing;
  Mar cog Δ=$29 stays within band.
- **0 INVESTIGATE vs prior pull** (clean pull-to-pull baseline).
- These will collapse to 0 once the workbook cog is corrected and the
  FBA drift accepts a fresh Sellerise snapshot.

Perturbation acceptance test (cog × 1.20) fires **6/6 UK months** on
vs-Sellerise cog (up from 4/6 with the old $500 band) plus 6/6 on both
vs-prior guards. US/CA numbers unchanged.

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
| 2026-05 | +$494 | **−$436** | Ads landed (C$929.95 EXACT vs Sellerise) |
| 2026-06 | −$45 | **−$793** | Trailing DEFERRED; Ads landed (C$747.92 EXACT) |
| **Σ Jan-Apr (ads-complete)** | **+$5,271** | **−$1,546** | pre-cog-fix numbers |
| **Σ Jan-Jun** | **+$5,719** | **−$2,774** | pre-cog-fix numbers |

**After the CA cog fix** (`MARKETPLACE_COG_SOURCE_OVERRIDE: CA→US`,
`RESOLVE_CA_COG_RESIDUAL.md`):

| month | Δ after ads + cog fix | vs prior |
|---|---:|---|
| 2026-01 | **+$157** | was −$323 |
| 2026-02 | **+$17**  | was −$532 |
| 2026-03 | **+$11**  | was −$422 |
| 2026-04 | **−$1**   | was −$269 |
| 2026-05 | **−$339** | was −$436 |
| 2026-06 | **−$219** | was −$793 |
| **Σ Jan-Jun** | **−$374** (mixed-sign) | was −$2,774 all-negative |

CA now behaves like UK: small mixed-sign drift, within the tightened $500
cog band.

## CA residual: RESOLVED (per `RESOLVE_CA_COG_RESIDUAL.md`)

**Update — the prior "CA cog value drift, unfixable data governance" verdict
was wrong** and its own evidence contradicted it. Re-diagnosis under
`RESOLVE_CA_COG_RESIDUAL.md` traced the residual to a fixable FX-derived
cost-basis bug in the CA workbook sheet. Fix landed in
`MARKETPLACE_COG_SOURCE_OVERRIDE` (CA cog now sources from US per-SKU values,
matching UK's approach). Post-fix CA Σ Jan-Jun net Δ dropped from
**−$2,774 → −$374** (mixed-sign), CA cog band tightened from $1,000 → $500.

### Decomposition (CA settled ads-complete months Jan-Apr)

For every month, cog Δ dominates the net Δ; all other cells are small
mixed-sign drift (like UK). Sum of per-bucket contributions ≈ net Δ within
$5 rounding.

| month | net Δ after | cog Δ (contributes negatively to net) | other cells sum | rounding |
|---|---:|---:|---:|---:|
| 2026-01 | −$322.77 | −$337.86 | +$15.09 | 0 |
| 2026-02 | −$532.11 | −$344.49 | −$187.62 | 0 |
| 2026-03 | −$421.51 | −$599.82 | +$178.31 | 0 |
| 2026-04 | −$268.91 | −$258.52 | −$10.39 | 0 |

The per-bucket contributions ARE named individually (see
`reference/data/reconcile_report_CA.md` Section 2026-01..2026-04):
- **cog** (+$258 to +$632, same-signed positive): the systematic driver
- `chargesObject.Principal`, `chargesObject.Tax`: month-boundary attribution
  swaps in Feb→Mar ±$199.50 / ±$9.98 (Sellerise's own restatement)
- `fbaObject.FBAPerUnitFulfillmentFee`: mixed-sign ±$8 to ±$48
- `feesObject.Commission`: mixed-sign ±$3 to ±$30
- `refundsObject.*`: small drift under $50/cell/month
- `storageFee`, `expenses`: matches to within 30¢/month

### Mechanism ruled out (Step 3)

1. **All refund statuses correctly netted.** DB inspection: CA has RELEASED
   (non-release-event), DEFERRED, and DEFERRED_RELEASED Refund/Shipment rows;
   the current WHERE clause `is_deferred_release_event=false` correctly
   excludes only the release events (which would double-count against
   `DEFERRED_RELEASED`). Not the US failure mode.
2. **Missing SKUs are small and wrong-direction.** 7 CA SKUs have sales but
   no COGS row (`cogs_missing_skus`), totaling 1-8 units/month. Missing
   COGS understates our cog (→ *smaller* number), but our cog is
   systematically *larger* than Sellerise's. Cannot be the driver.
3. **Attribution winner is empirical.** Tested all four
   shipment×refund basis combos:
   - shipment=posted, refund=posted: Σ|Δ| still $2,939
   - shipment=posted, refund=purchase: worse
   - shipment=purchase, refund=posted (**current CA config**): Σ|Δ| $2,597 (winner)
   - shipment=purchase, refund=purchase (US config): Σ|Δ| $3,090
   No basis eliminates the residual. Algorithm is not the driver.

### Root cause (Step 4, corrected): FX-derived cost-basis bug in the CA sheet

The prior "per-SKU value drift" verdict was **self-contradictory**: it cited
CA cog = US cog × 1.35 (mechanically derived) alongside "per-SKU value
drift" (independent drift). Both can't be true. Re-diagnosis under
`RESOLVE_CA_COG_RESIDUAL.md`:

- **Step 1 (structure):** every CA per-SKU cog is US per-SKU cog × exactly
  1.35 (ratio 1.3493–1.3512 across all 11 CA SKUs; CA prices are US ×
  1.144, a different multiplier — so the CA sheet was mechanically FX-marked
  up at some point). Not independently entered CA costs.
- **Step 2 (SKU-vs-month split):** the observed month-to-month ratio
  Sellerise/Ours (0.68–0.85) is NOT well-explained by per-SKU cost drift —
  ridge-anchored LOO-CV per-SKU model produces Σ|Δ| = $651 vs $636 for the
  simple "Sellerise uses US cog directly" null (per-SKU is worse). The
  ratio swing is dominated by SKU mix, and the mix-adjusted null model is
  a flat, marketplace-wide "no ×1.35" correction.
- **Step 3 (fix simulation):** substituting US per-SKU cog values for CA
  (i.e. removing the workbook's ×1.35 markup) collapses:
  - Σ|Δ| cog: **$2,597 → $909** (down 65%)
  - shape: **all-negative same-signed → mixed-sign** (Jan −142, Feb −205,
    Mar +168, Apr −9, May +328, Jun +58)
  - CA Σ Jan-Jun net Δ: **−$2,774 → −$374**
- **UK control:** the UK sheet uses ≈US-parity cog values (UK GMAKER-3 =
  30.94 vs US 30.76). UK residual is small mixed-sign — precisely the
  pattern CA now matches after the fix.

### Fix landed

- Added `MARKETPLACE_COG_SOURCE_OVERRIDE` in
  [`config.py`](../../backend/sync/config.py): CA → US per-SKU cog lookup.
- Wired into [`reconcile.py`](../../backend/sync/reconcile.py)
  `compute_cog_by_basis` and [`cogs.py`](../../backend/sync/cogs.py)
  `compute_monthly_cogs` via the new `cog_source_marketplace()` helper.
- **Not** applied as a flat multiplier — the join is redirected to a
  different marketplace's `cogs_per_sku` values (per the task guardrail).
- CA cog band tightened **from $1,000 to $500** (matches UK, 1.5x margin
  over post-fix max |Δ| = $328).
- US, UK reconciles unchanged (override empty for them). All three
  marketplaces: **0 INVESTIGATE / 0 INVESTIGATE** on both guards.
- Perturbation test still fires: cog × 1.20 catches 5/6 (US), 1/6 (CA on
  vs-Sellerise, wide-band by design), 4/6 (UK) plus 6/6 on all
  vs-prior-pull.

### Provisional status

The override treats US per-SKU cog as CA's cost basis because empirically
that's what Sellerise appears to use. If real CA-sourced per-unit costs
land in the CA sheet (with actual sourcing + duties + freight — not a flat
FX markup), remove the override entry and revalidate the residual.

### US (regression baseline — MUST stay clean)

```
Drift-guards: 0 INVESTIGATE on both (vs Sellerise + vs prior pull).
Locked targets: 9/15 PASS.
```

US reconciliation unchanged by rollout work — the added rules
(DigitalServicesFee, VAT family, ShippingTaxDiscount passthrough) don't
affect US leaves.

## Per-marketplace drift bands (closes the monitoring gap)

Added `DRIFT_BANDS_BY_MARKETPLACE` and `PRIOR_PULL_BANDS_BY_MARKETPLACE` in
[`backend/sync/drift_bands.py`](../../backend/sync/drift_bands.py). Bands are
derived from each marketplace's own observed drift, never copied from US.

### Verification: 0 INVESTIGATE clean

After all May+Jun ads land and a fresh baseline persists:

```
US: Drift-guards: 0 INVESTIGATE on both (vs Sellerise + vs prior pull).
UK: Drift-guards: 0 INVESTIGATE on both (vs Sellerise + vs prior pull).
CA: Drift-guards: 0 INVESTIGATE on both (vs Sellerise + vs prior pull).
```

### Verification: perturbation acceptance test (cog × 1.20)

Same acceptance test as US baseline. All three marketplaces catch a 20 %
cog inflation on at least one guard:

| marketplace | vs-Sellerise cog fires | vs-prior-pull cog fires | vs-prior-pull net fires |
|---|---:|---:|---:|
| US | 5/6 months | 6/6 | 6/6 |
| CA | 1/6 months (Mar; band=$1000 absorbs smaller months) | 6/6 | 6/6 |
| UK | 4/6 months | 6/6 | 6/6 |

CA's vs-Sellerise cog band is wide ($1000) because it must absorb the CA
cog value drift documented above. The vs-prior-pull guard (CA cog band =
$15) is what catches subtler CA cog regressions — this is the vs-prior-pull
guard's exact design purpose, mirroring the US structural blindspot fix.

Key bands (per-marketplace, vs-Sellerise settled / vs-prior-pull):

| cell | US | CA | UK |
|---|---:|---:|---:|
| chargesObject.Principal | 1500 / 100 | 300 / 15 | 20 / 20 |
| feesObject.Commission   | 300 / 50   | 60 / 10  | 300 / 15 |
| fbaObject.FBAPerUnitFulfillmentFee | 400 / 50 | 100 / 10 | 250 / 15 |
| refundsObject.Principal | 400 / 50   | 100 / 10 | 250 / 15 |
| refundsObject.Tax Withheld | 30 / 10 | 5 / 2    | 150 / 3  |
| cog | 2500 / 100 | 1000 / 15 | 500 / 25 |
| net (derived, vs-prior-pull only) | 500 | 60 | 100 |

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

- ~~**CA/UK ads May+Jun**~~: **CLOSED** by
  [`CA_UK_RESIDUAL_CLOSEOUT.md`](../../CA_UK_RESIDUAL_CLOSEOUT.md) Step 1.
  All four months (CA/UK × May/Jun) pulled, persisted, and match Sellerise
  to the cent.
- ~~**Per-marketplace drift bands**~~: **CLOSED** by Step 5 —
  `DRIFT_BANDS_BY_MARKETPLACE` derived per-marketplace, acceptance test
  passes.
- ~~**CA remaining residual**~~: **FIXED** by `RESOLVE_CA_COG_RESIDUAL.md`
  as an FX-derived cost-basis bug in the CA workbook sheet, not "unfixable
  value drift." CA cog now sources from US per-SKU values via
  `MARKETPLACE_COG_SOURCE_OVERRIDE`. Σ Jan-Jun net Δ dropped from −$2,774
  → −$374 (mixed-sign).
- **AU rollout**: blocked on Sellerise target. Structural probe already done;
  inferred mappings ready to commit once verified.
- **CA workbook cost basis** *(remaining data-governance action)*: the CA
  sheet of `COGS_Magical_Butter_1.xlsx` still contains US×1.35 rows; the
  code override compensates. Replacing with real CA-sourced per-unit
  costs (with actual sourcing + duties + freight) would allow removing the
  override; not blocking.

## Files touched

- [`backend/sync/config.py`](../../backend/sync/config.py) — added
  `MARKETPLACE_REFUND_COGS_BASIS`, `MARKETPLACE_AD_CURRENCY` alias, and
  `MARKETPLACE_COG_SOURCE_OVERRIDE` with `cog_source_marketplace()` helper
  (CA→US per-SKU cog to fix the workbook's US×1.35 basis).
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
  `compute_cog_by_basis`; drift-guard calls now pass `marketplace_id`.
- [`backend/sync/drift_bands.py`](../../backend/sync/drift_bands.py) —
  added `DRIFT_BANDS_BY_MARKETPLACE` and `PRIOR_PULL_BANDS_BY_MARKETPLACE`
  (US/CA/UK), per-marketplace ad bands, `ad_bands_for()` and
  `prior_pull_ad_bands_for()` helpers. `band_for()` and
  `prior_pull_band_for()` accept optional `marketplace_id`; US remains the
  default for legacy callers.

No US number changed. No AU committed.
