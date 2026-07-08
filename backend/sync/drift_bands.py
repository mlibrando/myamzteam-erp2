"""Per-bucket drift bands for the monthly reconciliation regression guard.

Purpose: distinguish restatement drift (expected — Amazon revises numbers post-hoc,
Sellerise's snapshot is frozen at one point in time) from a pipeline regression
(possible bug — our code, mapping, or attribution changed).

Bands are the maximum |Δ vs Sellerise| we accept without INVESTIGATE. Derived
from the observed max abs per-settled-month Δ per cell (see
`reference/data/drift_baseline.md` for the derivation table), with a 1.5x-2x
margin so a small additional Amazon restatement between pulls does not cry
wolf.

Design:
- **Per marketplace.** US/CA/UK have different scale, different Sellerise
  classification quirks, and different tax/fee families. Copying US $ bands to
  CA (≈1/10 US scale) would make the guard blind to CA-scale regressions; UK
  has Sellerise-only cells (ReferralFee split, FBAFees split) that need wider
  bands than US. Every marketplace's bands come from its own observed drift.
- **Settled** month bands: apply to Jan-May (in current data). Anything outside
  the band on a settled bucket is `INVESTIGATE`.
- **Trailing** month bands: apply to the latest Sellerise-covered month (Jun in
  current data), which is still moving (refund lag, DEFERRED estimates). Widen
  by TRAILING_MULTIPLIER.
- Empirical fact: over a ~13-hour window on 2026-07-07, Amazon returned exact
  same numbers pull-to-pull (Σ|Δ| = $0.00 for ads). The observed drift over
  weeks/months between Sellerise's snapshot and our pull is the pattern the
  bands must accommodate; sub-daily drift is negligible.
"""

from __future__ import annotations

from decimal import Decimal

# ── US bands ────────────────────────────────────────────────────────────────
# Basis: max |Δ| observed across settled months Jan-May (post-refund-COGS-fix),
# 1.5x-2x margin. Match-to-cent cells get $5.
_US_SETTLED_BANDS: dict[tuple[str, str], Decimal] = {
    # chargesObject
    ("chargesObject", "Principal"):            Decimal("1500"),   # obs max 981
    ("chargesObject", "Tax"):                  Decimal("200"),    # obs max 80
    ("chargesObject", "ShippingCharge"):       Decimal("200"),    # obs max 79
    ("chargesObject", "ShippingTax"):          Decimal("20"),     # obs max 8
    ("chargesObject", "Promotion"):            Decimal("60"),     # decision-E residual
    ("chargesObject", "GiftWrap"):             Decimal("5"),
    ("chargesObject", "GiftWrapTax"):          Decimal("5"),
    ("chargesObject", "Shipping"):             Decimal("200"),    # Sellerise-only line
    # feesObject
    ("feesObject", "Commission"):              Decimal("300"),    # obs max 149
    ("feesObject", "ShippingChargeback"):      Decimal("120"),    # obs max 79
    ("feesObject", "GiftwrapChargeback"):      Decimal("5"),
    ("feesObject", "ReferralFee"):             Decimal("5"),      # decision A: 0 settled
    ("feesObject", "POAServiceFee"):           Decimal("5"),
    ("feesObject", "PoAPerUnitFulfillmentFee"): Decimal("15"),
    # fbaObject
    ("fbaObject", "FBAPerUnitFulfillmentFee"): Decimal("400"),    # obs max 202
    ("fbaObject", "FBAFees"):                  Decimal("5"),      # decision A: 0 settled
    # refundsObject
    ("refundsObject", "Principal"):            Decimal("400"),    # obs max 297
    ("refundsObject", "Commission"):           Decimal("100"),    # obs max 45
    ("refundsObject", "RefundCommission"):     Decimal("20"),
    ("refundsObject", "Promotion"):            Decimal("20"),
    ("refundsObject", "Tax"):                  Decimal("30"),
    ("refundsObject", "Tax Withheld"):         Decimal("30"),
    ("refundsObject", "ShippingCharge"):       Decimal("30"),
    ("refundsObject", "ShippingChargeback"):   Decimal("30"),
    ("refundsObject", "ShippingTax"):          Decimal("5"),
    ("refundsObject", "GiftWrap"):             Decimal("5"),
    ("refundsObject", "GiftWrapTax"):          Decimal("5"),
    ("refundsObject", "GiftwrapChargeback"):   Decimal("5"),
    ("refundsObject", "RestockingFee"):        Decimal("5"),
    ("refundsObject", "Goodwill"):             Decimal("5"),
    # scalars / derived
    ("storageFee", "(scalar)"):                Decimal("5"),
    ("salesTaxes", "(derived)"):               Decimal("250"),
    # cog: Jan pre-backfill boundary = $2019 (documented structural).
    ("cog", "(scalar)"):                       Decimal("2500"),
}

# ── CA bands ────────────────────────────────────────────────────────────────
# CA is ~1/10 US scale. Basis: observed |Δ| over Jan-Jun after the CA cog
# fix (MARKETPLACE_COG_SOURCE_OVERRIDE routes CA cog to US per-SKU values —
# the CA sheet's US×1.35 markup was a spurious FX-like multiplier that
# produced a same-signed $258-$632/mo residual, resolved by
# RESOLVE_CA_COG_RESIDUAL.md). Post-fix CA cog |Δ| max = $328 (May),
# median ~$180, mixed-sign — same class as UK small drift.
_CA_SETTLED_BANDS: dict[tuple[str, str], Decimal] = {
    # chargesObject
    ("chargesObject", "Principal"):            Decimal("300"),    # obs max 199.50
    ("chargesObject", "Tax"):                  Decimal("25"),     # obs max 9.98
    ("chargesObject", "Promotion"):            Decimal("10"),
    ("chargesObject", "ShippingCharge"):       Decimal("20"),
    ("chargesObject", "ShippingTax"):          Decimal("5"),
    # feesObject
    ("feesObject", "Commission"):              Decimal("60"),     # obs max 29.93
    ("feesObject", "ShippingChargeback"):      Decimal("10"),
    # fbaObject
    ("fbaObject", "FBAPerUnitFulfillmentFee"): Decimal("100"),    # obs max 47.75
    ("fbaObject", "FBAFees"):                  Decimal("30"),     # trailing-DEFERRED margin
    # refundsObject
    ("refundsObject", "Principal"):            Decimal("100"),    # obs max 49.90
    ("refundsObject", "Commission"):           Decimal("20"),     # obs max 7.08
    ("refundsObject", "DigitalServicesFee"):   Decimal("5"),
    ("refundsObject", "Promotion"):            Decimal("10"),
    ("refundsObject", "RefundCommission"):     Decimal("5"),
    ("refundsObject", "ShippingCharge"):       Decimal("5"),
    ("refundsObject", "Tax"):                  Decimal("5"),
    ("refundsObject", "Tax Withheld"):         Decimal("5"),
    # scalars / derived
    ("storageFee", "(scalar)"):                Decimal("5"),      # matches to cent
    ("salesTaxes", "(derived)"):               Decimal("25"),     # obs max 9.98
    # cog: post-fix obs max 327.92 (May), median ~180 mixed-sign. Band 500 =
    # ~1.5x margin, matching UK. Down from 1000 which was compensation for
    # the now-fixed US×1.35 cost-basis bug (see RESOLVE_CA_COG_RESIDUAL.md).
    ("cog", "(scalar)"):                       Decimal("500"),
    ("expenses", "(aggregate)"):               Decimal("5"),
}

# ── UK bands ────────────────────────────────────────────────────────────────
# UK is ~1/6 US scale. Basis: observed |Δ| Jan-Jun from
# reference/data/reconcile_report_UK.md. Two systematic drivers are UNFIXED
# pending workbook / Sellerise updates (see UK_RESIDUAL_DIAGNOSIS.md):
#   - cog: per-SKU workbook cog values are ~$1/unit too high ($0.17-$3.01/u
#     gap × units → +$29-$244/mo Δ, all six months same-signed positive).
#     LOO-CV shows the true per-SKU costs exist and would collapse Σ|Δ|
#     from $1001 to ~$207 if the workbook is corrected. Not a pipeline
#     mechanism.
#   - fbaObject: Sellerise's per-unit FBA rate is ~10% lower than the raw
#     Amazon sp_breakdowns rate — classic post-snapshot restatement drift.
#     Same-signed −$60-$135/mo.
# Bands here are sized to the POST-FIX residual (small mixed-sign like UK
# would look after workbook + FBA reconcile), so at the current UNRESOLVED
# state they INVESTIGATE — the honest signal that these residuals need
# attention. Once fixed, INVESTIGATE goes quiet naturally.
_UK_SETTLED_BANDS: dict[tuple[str, str], Decimal] = {
    # chargesObject
    ("chargesObject", "Principal"):            Decimal("20"),     # matches to cent
    ("chargesObject", "Tax"):                  Decimal("20"),
    ("chargesObject", "Promotion"):            Decimal("50"),     # obs max 24.88
    ("chargesObject", "ShippingCharge"):       Decimal("10"),     # obs max 2.08
    ("chargesObject", "ShippingTax"):          Decimal("5"),
    ("chargesObject", "Shipping"):             Decimal("10"),     # Sellerise-only, obs max 2.50
    ("chargesObject", "GiftWrap"):             Decimal("5"),
    ("chargesObject", "GiftWrapTax"):          Decimal("5"),
    # feesObject
    # Sellerise's split (Commission ↔ ReferralFee) cancels in every settled
    # month except Jan (−$118); Commission band captures that plus a small
    # regression margin.
    ("feesObject", "Commission"):              Decimal("200"),    # obs max 153.28
    ("feesObject", "ShippingChargeback"):      Decimal("10"),
    ("feesObject", "DigitalServicesFee"):      Decimal("5"),
    ("feesObject", "DigitalServicesFeeFBA"):   Decimal("5"),
    ("feesObject", "GiftwrapChargeback"):      Decimal("5"),
    ("feesObject", "ReferralFee"):             Decimal("100"),    # obs max 67.46
    # fbaObject — SIZED TO POST-RESTATEMENT-FIX, not current drift.
    # Current UK FBA Δ is systematic $60-135/mo drift (Amazon post-snapshot
    # rate revision). Band 50 fires on the drift so it's not hidden.
    ("fbaObject", "FBAPerUnitFulfillmentFee"): Decimal("50"),
    ("fbaObject", "FBAFees"):                  Decimal("25"),     # obs max 17.84
    # refundsObject
    ("refundsObject", "Principal"):            Decimal("200"),    # obs max 134.55
    ("refundsObject", "Commission"):           Decimal("30"),     # obs max 15.06
    ("refundsObject", "DigitalServicesFee"):   Decimal("5"),
    ("refundsObject", "Promotion"):            Decimal("10"),
    ("refundsObject", "RefundCommission"):     Decimal("10"),
    ("refundsObject", "ShippingCharge"):       Decimal("5"),
    ("refundsObject", "ShippingChargeback"):   Decimal("5"),
    ("refundsObject", "ShippingTax"):          Decimal("5"),
    ("refundsObject", "Tax"):                  Decimal("60"),     # obs max 26.91
    # Tax Withheld tracks DEFERRED refund lag — wider band per obs 63.50.
    ("refundsObject", "Tax Withheld"):         Decimal("100"),
    # scalars / derived
    # UK storageFee: Sellerise reclassifies ServiceFee.FBAStorageFee into
    # expenses.FBAFees for some months (May: 77.60, Jun: 59.68 in raw data).
    # Widened to accommodate. Non-reclassified months match to cent.
    ("storageFee", "(scalar)"):                Decimal("100"),
    ("salesTaxes", "(derived)"):               Decimal("20"),
    # cog: SIZED TO POST-WORKBOOK-FIX residual (LOO-CV Σ|Δ|=$207 → max
    # ~$40-70/mo). Band 100 fires on months where the current per-SKU value
    # gap exceeds that (Jan +$243, Feb +$178, Apr +$184, May +$123, Jun +$244).
    # Once the workbook is corrected, INVESTIGATE goes quiet.
    ("cog", "(scalar)"):                       Decimal("100"),
    ("expenses", "(aggregate)"):               Decimal("80"),     # obs max 45.24
}

# Backward-compat alias — the legacy single-marketplace name still used by
# any callers that haven't been migrated. New code should call band_for(...)
# with a marketplace_id.
SETTLED_BANDS = _US_SETTLED_BANDS

DRIFT_BANDS_BY_MARKETPLACE: dict[str, dict[tuple[str, str], Decimal]] = {
    "ATVPDKIKX0DER":  _US_SETTLED_BANDS,
    "A2EUQ1WTGCTBG2": _CA_SETTLED_BANDS,
    "A1F83G8C2ARO7P": _UK_SETTLED_BANDS,
    # AU is quarantined — no Sellerise target, no bands defined.
}

# ── Ad-line bands (per marketplace) ─────────────────────────────────────────
# Ads reconcile to the cent for CA/UK Jan-Apr; keep tight. US ads observe
# ±$5.75 max, hence $10/line, $30/TOTAL bands.
_US_AD_LINE_BAND  = Decimal("10")
_US_AD_TOTAL_BAND = Decimal("30")
# CA/UK ads are ~1/2-1/3 of US ad scale; keep the same $10/$30 for headroom
# but the observed |Δ| is $0.00 in Jan-Apr.
_CA_AD_LINE_BAND  = Decimal("10")
_CA_AD_TOTAL_BAND = Decimal("30")
_UK_AD_LINE_BAND  = Decimal("10")
_UK_AD_TOTAL_BAND = Decimal("30")

# Legacy names kept for backward compat.
AD_LINE_BAND    = _US_AD_LINE_BAND
AD_TOTAL_BAND   = _US_AD_TOTAL_BAND

_AD_BANDS_BY_MARKETPLACE: dict[str, tuple[Decimal, Decimal]] = {
    "ATVPDKIKX0DER":  (_US_AD_LINE_BAND, _US_AD_TOTAL_BAND),
    "A2EUQ1WTGCTBG2": (_CA_AD_LINE_BAND, _CA_AD_TOTAL_BAND),
    "A1F83G8C2ARO7P": (_UK_AD_LINE_BAND, _UK_AD_TOTAL_BAND),
}


def ad_bands_for(marketplace_id: str | None) -> tuple[Decimal, Decimal]:
    """Return (per_line_band, total_band) for the marketplace, US as default."""
    return _AD_BANDS_BY_MARKETPLACE.get(marketplace_id or "", (_US_AD_LINE_BAND, _US_AD_TOTAL_BAND))


# Net formula sum can amplify per-bucket bands; the net-line band accepts up
# to the sum of the bucket bands touching it, capped.
NET_BAND        = Decimal("5000")

# The trailing month is still moving (refund lag, DEFERRED estimates). Widen
# bands by this factor for the trailing month only.
TRAILING_MULTIPLIER = Decimal("3")


def band_for(bucket: str, sub_line: str, is_trailing: bool,
             marketplace_id: str | None = None) -> Decimal:
    """Return the drift band for one cell, adjusting for trailing regime.

    Per-marketplace bands come from DRIFT_BANDS_BY_MARKETPLACE. Callers
    should pass `marketplace_id`; if omitted (legacy call sites) falls back
    to US bands.
    """
    bands = DRIFT_BANDS_BY_MARKETPLACE.get(marketplace_id or "", _US_SETTLED_BANDS)
    base = bands.get((bucket, sub_line))
    if base is None:
        # A cell without a defined band — default very generous so we don't
        # cry wolf on unmapped things (they'd get logged separately as
        # unmapped, not as regression signal).
        base = Decimal("10000")
    if is_trailing:
        return base * TRAILING_MULTIPLIER
    return base


def classify(delta: Decimal, band: Decimal, is_trailing: bool) -> str:
    """Return WITHIN_DRIFT | TRAILING | INVESTIGATE."""
    if is_trailing:
        return "TRAILING" if abs(delta) < band else "INVESTIGATE"
    return "WITHIN_DRIFT" if abs(delta) < band else "INVESTIGATE"


# ── vs-prior-pull bands (much tighter — pure pull-to-pull drift) ────────────
# Baseline empirical: ads returned $0.00 over a ~13-hour window on 2026-07-07.
# Restatement accumulates on week-to-month scales, so a settled month's pure
# drift between two pulls (or two identical re-runs of reconcile) is small.
# Bands here are calibrated to catch systematic per-cell shifts (e.g. a code
# regression that flips or replaces a bucket's math) without crying wolf on
# expected Amazon restatement.
#
# **Distinct from vs-Sellerise bands.** The vs-Sellerise bands (above) are wide
# because they absorb our-vs-them attribution residuals like the Jan
# pre-backfill boundary; vs-prior-pull bands are our-now vs our-then and
# absorb only true pull-to-pull movement.
#
# CA/UK scale down from US bands: CA is ~1/10 US scale; UK is ~1/6.
_US_PRIOR_PULL_BANDS: dict[tuple[str, str], Decimal] = {
    ("storageFee", "(scalar)"):                Decimal("1"),
    ("chargesObject", "GiftWrap"):             Decimal("1"),
    ("chargesObject", "GiftWrapTax"):          Decimal("1"),
    ("feesObject", "GiftwrapChargeback"):      Decimal("1"),
    ("feesObject", "ReferralFee"):             Decimal("1"),
    ("fbaObject", "FBAFees"):                  Decimal("1"),
    ("refundsObject", "GiftWrap"):             Decimal("1"),
    ("refundsObject", "GiftWrapTax"):          Decimal("1"),
    ("refundsObject", "GiftwrapChargeback"):   Decimal("1"),
    ("refundsObject", "RestockingFee"):        Decimal("1"),
    ("refundsObject", "Goodwill"):             Decimal("1"),
    ("refundsObject", "ShippingTax"):          Decimal("1"),
    ("chargesObject", "ShippingTax"):          Decimal("5"),
    ("chargesObject", "Promotion"):            Decimal("5"),
    ("feesObject", "ShippingChargeback"):      Decimal("10"),
    ("refundsObject", "RefundCommission"):     Decimal("5"),
    ("refundsObject", "Promotion"):            Decimal("5"),
    ("refundsObject", "Tax"):                  Decimal("10"),
    ("refundsObject", "Tax Withheld"):         Decimal("10"),
    ("refundsObject", "ShippingCharge"):       Decimal("5"),
    ("refundsObject", "ShippingChargeback"):   Decimal("5"),
    ("chargesObject", "Principal"):            Decimal("100"),
    ("chargesObject", "Tax"):                  Decimal("30"),
    ("chargesObject", "ShippingCharge"):       Decimal("20"),
    ("chargesObject", "Shipping"):             Decimal("10"),
    ("feesObject", "Commission"):              Decimal("50"),
    ("fbaObject", "FBAPerUnitFulfillmentFee"): Decimal("50"),
    ("refundsObject", "Principal"):            Decimal("50"),
    ("refundsObject", "Commission"):           Decimal("20"),
    ("cog", "(scalar)"):                       Decimal("100"),
    ("salesTaxes", "(derived)"):               Decimal("30"),
    # net band chosen to still catch a ~$2.8k cog regression (the acceptance
    # test) — much tighter than the vs-Sellerise net band ($5,000).
    ("net", "(derived)"):                      Decimal("500"),
}

# CA vs-prior-pull: 1/10 US scale. Aggregates scaled proportionally so
# perturbations sized to CA still fire; match-to-cent cells stay at $1.
_CA_PRIOR_PULL_BANDS: dict[tuple[str, str], Decimal] = {
    ("storageFee", "(scalar)"):                Decimal("1"),
    ("chargesObject", "GiftWrap"):             Decimal("1"),
    ("chargesObject", "GiftWrapTax"):          Decimal("1"),
    ("feesObject", "GiftwrapChargeback"):      Decimal("1"),
    ("fbaObject", "FBAFees"):                  Decimal("1"),
    ("refundsObject", "GiftWrap"):             Decimal("1"),
    ("refundsObject", "GiftWrapTax"):          Decimal("1"),
    ("refundsObject", "GiftwrapChargeback"):   Decimal("1"),
    ("refundsObject", "RestockingFee"):        Decimal("1"),
    ("refundsObject", "Goodwill"):             Decimal("1"),
    ("refundsObject", "ShippingTax"):          Decimal("1"),
    ("refundsObject", "DigitalServicesFee"):   Decimal("1"),
    ("chargesObject", "ShippingTax"):          Decimal("2"),
    ("chargesObject", "Promotion"):            Decimal("2"),
    ("feesObject", "ShippingChargeback"):      Decimal("2"),
    ("refundsObject", "RefundCommission"):     Decimal("2"),
    ("refundsObject", "Promotion"):            Decimal("2"),
    ("refundsObject", "Tax"):                  Decimal("2"),
    ("refundsObject", "Tax Withheld"):         Decimal("2"),
    ("refundsObject", "ShippingCharge"):       Decimal("2"),
    ("refundsObject", "ShippingChargeback"):   Decimal("2"),
    ("chargesObject", "Principal"):            Decimal("15"),
    ("chargesObject", "Tax"):                  Decimal("5"),
    ("chargesObject", "ShippingCharge"):       Decimal("2"),
    ("feesObject", "Commission"):              Decimal("10"),
    ("fbaObject", "FBAPerUnitFulfillmentFee"): Decimal("10"),
    ("refundsObject", "Principal"):            Decimal("10"),
    ("refundsObject", "Commission"):           Decimal("5"),
    ("cog", "(scalar)"):                       Decimal("15"),
    ("salesTaxes", "(derived)"):               Decimal("5"),
    ("expenses", "(aggregate)"):               Decimal("2"),
    # net band scaled to catch a ~$300 cog regression (CA-sized perturbation).
    ("net", "(derived)"):                      Decimal("60"),
}

# UK vs-prior-pull: ~1/6 US scale. Wider than CA on cells UK actually uses,
# tighter on Sellerise-only cells UK doesn't emit (ReferralFee, FBAFees).
_UK_PRIOR_PULL_BANDS: dict[tuple[str, str], Decimal] = {
    ("storageFee", "(scalar)"):                Decimal("1"),
    ("chargesObject", "GiftWrap"):             Decimal("1"),
    ("chargesObject", "GiftWrapTax"):          Decimal("1"),
    ("feesObject", "GiftwrapChargeback"):      Decimal("1"),
    ("feesObject", "ReferralFee"):             Decimal("1"),
    ("feesObject", "DigitalServicesFee"):      Decimal("1"),
    ("feesObject", "DigitalServicesFeeFBA"):   Decimal("1"),
    ("fbaObject", "FBAFees"):                  Decimal("1"),
    ("refundsObject", "GiftWrap"):             Decimal("1"),
    ("refundsObject", "GiftwrapChargeback"):   Decimal("1"),
    ("refundsObject", "ShippingTax"):          Decimal("1"),
    ("refundsObject", "DigitalServicesFee"):   Decimal("1"),
    ("chargesObject", "ShippingTax"):          Decimal("2"),
    ("chargesObject", "Promotion"):            Decimal("3"),
    ("chargesObject", "Shipping"):             Decimal("2"),
    ("feesObject", "ShippingChargeback"):      Decimal("3"),
    ("refundsObject", "RefundCommission"):     Decimal("2"),
    ("refundsObject", "Promotion"):            Decimal("2"),
    ("refundsObject", "Tax"):                  Decimal("3"),
    ("refundsObject", "Tax Withheld"):         Decimal("3"),
    ("refundsObject", "ShippingCharge"):       Decimal("2"),
    ("refundsObject", "ShippingChargeback"):   Decimal("2"),
    ("chargesObject", "Principal"):            Decimal("20"),
    ("chargesObject", "Tax"):                  Decimal("10"),
    ("chargesObject", "ShippingCharge"):       Decimal("5"),
    ("feesObject", "Commission"):              Decimal("15"),
    ("fbaObject", "FBAPerUnitFulfillmentFee"): Decimal("15"),
    ("refundsObject", "Principal"):            Decimal("15"),
    ("refundsObject", "Commission"):           Decimal("5"),
    ("cog", "(scalar)"):                       Decimal("25"),
    ("salesTaxes", "(derived)"):               Decimal("5"),
    ("expenses", "(aggregate)"):               Decimal("5"),
    # net band scaled to catch a ~$500 cog regression (UK-sized perturbation).
    ("net", "(derived)"):                      Decimal("100"),
}

# Backward-compat alias.
PRIOR_PULL_BANDS = _US_PRIOR_PULL_BANDS

PRIOR_PULL_BANDS_BY_MARKETPLACE: dict[str, dict[tuple[str, str], Decimal]] = {
    "ATVPDKIKX0DER":  _US_PRIOR_PULL_BANDS,
    "A2EUQ1WTGCTBG2": _CA_PRIOR_PULL_BANDS,
    "A1F83G8C2ARO7P": _UK_PRIOR_PULL_BANDS,
}

# Ad-side vs-prior-pull bands. Ads reproduce $0.00 pull-to-pull, so keep tight.
# CA/UK smaller scale but observed drift is also $0.00 → same $3/$10.
_US_PRIOR_PULL_AD_LINE_BAND  = Decimal("3")
_US_PRIOR_PULL_AD_TOTAL_BAND = Decimal("10")
_CA_PRIOR_PULL_AD_LINE_BAND  = Decimal("3")
_CA_PRIOR_PULL_AD_TOTAL_BAND = Decimal("10")
_UK_PRIOR_PULL_AD_LINE_BAND  = Decimal("3")
_UK_PRIOR_PULL_AD_TOTAL_BAND = Decimal("10")

PRIOR_PULL_AD_LINE_BAND  = _US_PRIOR_PULL_AD_LINE_BAND
PRIOR_PULL_AD_TOTAL_BAND = _US_PRIOR_PULL_AD_TOTAL_BAND

_PRIOR_PULL_AD_BANDS_BY_MARKETPLACE: dict[str, tuple[Decimal, Decimal]] = {
    "ATVPDKIKX0DER":  (_US_PRIOR_PULL_AD_LINE_BAND, _US_PRIOR_PULL_AD_TOTAL_BAND),
    "A2EUQ1WTGCTBG2": (_CA_PRIOR_PULL_AD_LINE_BAND, _CA_PRIOR_PULL_AD_TOTAL_BAND),
    "A1F83G8C2ARO7P": (_UK_PRIOR_PULL_AD_LINE_BAND, _UK_PRIOR_PULL_AD_TOTAL_BAND),
}


def prior_pull_ad_bands_for(marketplace_id: str | None) -> tuple[Decimal, Decimal]:
    """Return (per_line_band, total_band) prior-pull for the marketplace."""
    return _PRIOR_PULL_AD_BANDS_BY_MARKETPLACE.get(
        marketplace_id or "",
        (_US_PRIOR_PULL_AD_LINE_BAND, _US_PRIOR_PULL_AD_TOTAL_BAND),
    )


# Default for cells not listed
PRIOR_PULL_DEFAULT_BAND = Decimal("20")


def prior_pull_band_for(bucket: str, sub_line: str, is_trailing: bool,
                        marketplace_id: str | None = None) -> Decimal:
    """Return the vs-prior-pull drift band for one cell, trailing-aware."""
    bands = PRIOR_PULL_BANDS_BY_MARKETPLACE.get(marketplace_id or "", _US_PRIOR_PULL_BANDS)
    base = bands.get((bucket, sub_line), PRIOR_PULL_DEFAULT_BAND)
    if is_trailing:
        return base * TRAILING_MULTIPLIER
    return base
