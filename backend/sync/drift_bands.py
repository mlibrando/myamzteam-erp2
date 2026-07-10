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

from dataclasses import dataclass
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
# reference/data/reconcile_report_UK.md. Two systematic drivers, neither a
# pipeline mechanism:
#   - cog: SETTLED. Sellerise understates our per-SKU cost; the workbook is
#     validated against the component build-up. A Sellerise-side defect, now
#     pinned in TARGET_DEFECTS (4 settled cells). Do NOT edit the workbook.
#   - fbaObject: SETTLED. Sellerise books essentially no FBA fee for GMAKER-3
#     (£27.75 vs the £479.15 Amazon charged on the same 142 units). In five of
#     six months the whole bucket gap IS that SKU's fee, to the penny. Another
#     Sellerise-side defect, now pinned in TARGET_DEFECTS (5 settled cells).
#     The old label here, "post-snapshot restatement drift", was REFUTED first:
#     a re-pull of Feb and Mar 2026 returned 867 byte-identical transactions and
#     moved the FBA figure by £0.00. See reference/data/uk_fba_repull_test.md.
# Both bands stay as sized even though their cells are pinned: the pin holds each
# Δ at its measured value, and the band still governs any cell that leaves the
# registry. Neither was widened.
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
    # fbaObject — the 5 settled cells are PINNED in TARGET_DEFECTS (Sellerise
    # omits GMAKER-3's fee). This band is what catches any cell that is not, and
    # the trailing month. Not widened.
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


# ── Known target-side defects ───────────────────────────────────────────────
# A KNOWN_TARGET_DEFECT is a Δ diagnosed to the *reconciliation target*, not to
# our pipeline: our number is right and the target's is wrong. Widening a band
# to hide such a Δ would also blind that cell to a real regression, so instead
# we **pin** it. The Δ must stay at its measured magnitude within a tight
# tolerance; if it moves — in either direction, including toward zero because
# the target fixed its bug — the cell fires INVESTIGATE and someone re-reads
# the registry entry.
#
# This is not a band with a nicer name. `tolerance` is the cell's own measured
# noise floor (the vs-prior-pull band for Sellerise cells, the FX-granularity
# band for Sellerboard cells), never a multiple of the defect's size.
KNOWN_TARGET_DEFECT = "KNOWN_TARGET_DEFECT"


@dataclass(frozen=True)
class TargetDefect:
    """One pinned target-side defect.

    `expected_delta` is always **ours − theirs**, matching `reconcile.py`'s
    `diffs`. `reconcile_au.py` renders `theirs − ours` in its own table and
    negates before consulting this registry.
    """

    expected_delta: Decimal
    tolerance: Decimal
    note: str

    def matches(self, delta_ours_minus_theirs: Decimal) -> bool:
        return abs(delta_ours_minus_theirs - self.expected_delta) <= self.tolerance


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


def classify(delta: Decimal, band: Decimal, is_trailing: bool,
             defect: TargetDefect | None = None) -> str:
    """Return KNOWN_TARGET_DEFECT | WITHIN_DRIFT | TRAILING | INVESTIGATE.

    A registered defect takes precedence over the band, in both directions: the
    cell is KNOWN_TARGET_DEFECT only while `delta` sits at the defect's measured
    magnitude, and INVESTIGATE the moment it leaves that tolerance. It never
    falls back to the band — a pinned cell whose Δ has moved is a finding even
    if the new Δ happens to be small.
    """
    if defect is not None:
        return KNOWN_TARGET_DEFECT if defect.matches(delta) else "INVESTIGATE"
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


# ── The registry ────────────────────────────────────────────────────────────
# Keyed (marketplace_id, year_month, bucket, sub_line). See TargetDefect for the
# sign convention (ours − theirs) and the tolerance rule.
#
# Only cells whose defect breaches its band are registered. Where the same
# defect sits inside the band, the band already covers it and pinning would add
# nothing — each entry says which months those are.

_UK = "A1F83G8C2ARO7P"
_AU = "A39IBJ37TRP1C6"

_UK_COG_NOTE = (
    "Sellerise understates UK per-SKU cost. Our workbook is validated against the component "
    "cost build-up (ABDB 78.53, GMAKER-3 30.94, MBUKB1 96.06 — all tie out to invoice); "
    "Sellerise's values do not. Do NOT edit the workbook; do NOT retune our cog to match. "
    "Measured aggregate Δ Jan–Jun = +$1,000.62, of which 2026-03 (+29.34) and 2026-06 "
    "(+243.54, trailing) sit inside their bands and are not pinned here. "
    "OPEN: the relayed per-SKU magnitudes (ABDB ~28%, MBUKB1 ~2%) do not reconcile with that "
    "aggregate — 28% on ABDB alone implies +$2,484.69 — and Sellerise exposes only monthly "
    "aggregate cog, so per-SKU cannot be confirmed from this repo. The classification rests on "
    "the build-up table; the magnitude is open with Elena."
)

# The UK vs-prior-pull cog band is the calibrated 'how far may this cell legitimately
# move between two pulls' figure. Reuse it rather than inventing a tolerance.
_UK_COG_TOL = _UK_PRIOR_PULL_BANDS[("cog", "(scalar)")]   # $25

_AU_MCF_NOTE = (
    "Sellerboard counted exactly one Multi-Channel-Fulfilment unit (MBUKB1, ASIN B0CX1WMVQV) in "
    "2026-01, and correctly excludes MCF in the other five months. Our exclusion is right in all "
    "six: MCF orders carry SalesChannel='Non-Amazon' and Amazon posts no financial event, so "
    "listTransactions cannot return them. The one unit moves Jan cog (−86.71 = its workbook cog), "
    "commission (+30.07) and FBA fee (+30.27) — fees Amazon never billed us."
)

_AU_STORAGE_GST_NOTE = (
    "Sellerboard omitted GST from its 2026-01 `FBA storage fee` line; every other month it reports "
    "the GST-inclusive figure. Amazon did charge the GST — our ServiceFee.Tax of 77.40 is 10% of "
    "the 779.54 storage base. The billed-in-arrears hypothesis is refuted structurally: shifting "
    "one month fits 8x worse (Σ|Δ| 535.54 vs 64.17)."
)

_UK_FBA_NOTE = (
    "Sellerise books essentially NO FBA fulfilment fee for GMAKER-3. Amazon charged £479.15 over "
    "142 units Jan-Jun (£3.374/unit, straight off the `FBAPerUnitFulfillmentFee` leaves); Sellerise "
    "carries £27.75 for the same SKU and the same 142 units (£0.195/unit) — a 94.2% understatement. "
    "Proof it is the whole residual: in FIVE of six months the entire `fbaObject` bucket gap equals "
    "GMAKER-3's Amazon-charged fee TO THE PENNY (Jan -71.35, Feb -117.25, Mar -87.10, May -61.20, "
    "Jun -61.20; only April differs, by exactly £20.70, the one month Sellerise booked anything). "
    "Each pinned Δ decomposes exactly into (GMAKER-3's omitted fee) + (Sellerise's `FBAFees` "
    "deferred-estimate line, which we no longer have a counterpart for since those shipments "
    "released). Do NOT 'fix' our FBA figure: it is the fee Amazon actually billed. "
    "Two rival explanations are refuted, not merely unlikely: (1) Amazon post-snapshot restatement — "
    "a re-pull of Feb and Mar 2026 returned 867 byte-identical transactions and moved the FBA figure "
    "by £0.00, and `chargesObject.Principal` matches Sellerise to the cent in all six months; "
    "(2) netting of refunded units' fees — there are zero Refund-side FBA leaves anywhere in the UK "
    "feed and Sellerise's `refundsObject` has no FBA line. See reference/data/uk_fba_repull_test.md. "
    "NOTE the Δ scales with GMAKER-3's monthly unit volume, so a NEW month needs its own entry — "
    "and the right fix is Sellerise correcting the SKU's fee, which would drive these Δs to zero and "
    "(correctly) fire INVESTIGATE until the entries are removed."
)

# The UK vs-prior-pull band for this cell is the calibrated 'how far may it move
# between two pulls' figure. Reuse it rather than inventing a tolerance.
_UK_FBA_TOL = _UK_PRIOR_PULL_BANDS[("fbaObject", "FBAPerUnitFulfillmentFee")]   # £15

# AU tolerances are each cell's own FX-granularity band for that month
# (max(|ours_aud| x FX_RATE_TOLERANCE, $5.00)) — the residual a monthly rate can
# produce on its own. Below that, a move cannot be distinguished from FX noise;
# above it, the defect has changed.
TARGET_DEFECTS: dict[tuple[str, str, str, str], TargetDefect] = {
    # ── UK: Sellerise-side per-SKU cog understatement (4 settled cells) ──
    (_UK, "2026-01", "cog", "(scalar)"): TargetDefect(Decimal("242.84"), _UK_COG_TOL, _UK_COG_NOTE),
    (_UK, "2026-02", "cog", "(scalar)"): TargetDefect(Decimal("177.87"), _UK_COG_TOL, _UK_COG_NOTE),
    (_UK, "2026-04", "cog", "(scalar)"): TargetDefect(Decimal("184.41"), _UK_COG_TOL, _UK_COG_NOTE),
    (_UK, "2026-05", "cog", "(scalar)"): TargetDefect(Decimal("122.62"), _UK_COG_TOL, _UK_COG_NOTE),

    # ── UK: Sellerise omits GMAKER-3's FBA fee (5 settled cells) ──
    # 2026-06 carries the same defect (-61.20) but is the trailing month and is
    # still moving; its band handles it. Do not pin a trailing month.
    (_UK, "2026-01", "fbaObject", "FBAPerUnitFulfillmentFee"):
        TargetDefect(Decimal("-80.06"), _UK_FBA_TOL, _UK_FBA_NOTE),
    (_UK, "2026-02", "fbaObject", "FBAPerUnitFulfillmentFee"):
        TargetDefect(Decimal("-135.09"), _UK_FBA_TOL, _UK_FBA_NOTE),
    (_UK, "2026-03", "fbaObject", "FBAPerUnitFulfillmentFee"):
        TargetDefect(Decimal("-96.03"), _UK_FBA_TOL, _UK_FBA_NOTE),
    (_UK, "2026-04", "fbaObject", "FBAPerUnitFulfillmentFee"):
        TargetDefect(Decimal("-60.35"), _UK_FBA_TOL, _UK_FBA_NOTE),
    (_UK, "2026-05", "fbaObject", "FBAPerUnitFulfillmentFee"):
        TargetDefect(Decimal("-64.30"), _UK_FBA_TOL, _UK_FBA_NOTE),

    # ── AU: Sellerboard omitted GST from one storage line, one month ──
    (_AU, "2026-01", "storageFee", "storageFee"):
        TargetDefect(Decimal("52.75"), Decimal("17.00"), _AU_STORAGE_GST_NOTE),

    # ── AU: Sellerboard counted 1 of 3 MCF units in 2026-01 ──
    (_AU, "2026-01", "feesObject", "Commission"):
        TargetDefect(Decimal("30.07"), Decimal("19.24"), _AU_MCF_NOTE),
    (_AU, "2026-01", "fbaObject", "FBAPerUnitFulfillmentFee"):
        TargetDefect(Decimal("30.27"), Decimal("21.65"), _AU_MCF_NOTE),
    # cog is compared USD-to-USD with no FX on either side, so its tolerance is
    # cent-rounding, not an FX band. One more MCF unit would move it by ~86.71.
    (_AU, "2026-01", "cog", "(salesCosts)"):
        TargetDefect(Decimal("-86.71"), Decimal("1.00"), _AU_MCF_NOTE),
}


def target_defect_for(marketplace_id: str | None, year_month: str,
                      bucket: str, sub_line: str) -> TargetDefect | None:
    """The registered target-side defect for one cell, or None."""
    return TARGET_DEFECTS.get((marketplace_id or "", year_month, bucket, sub_line))
