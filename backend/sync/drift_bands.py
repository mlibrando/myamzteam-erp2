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

# ── Per (bucket, sub_line) drift band for a SETTLED month ───────────────────
# Format: (bucket, sub_line) → decimal_max_abs_delta_before_INVESTIGATE
#
# Basis for each band:
# - "obs max <VALUE>" = maximum |Δ| observed across settled months Jan-May
#   in `net_residual_diagnosis.md` (post-refund-COGS-fix state)
# - Multiplier of 1.5x-2x margin for extra restatement drift between pulls
# - Small "matches-to-cent" cells (storageFee, GiftWrap*, RestockingFee, etc.)
#   get $5 bands — if they move by more, something is wrong.
SETTLED_BANDS: dict[tuple[str, str], Decimal] = {
    # chargesObject
    ("chargesObject", "Principal"):            Decimal("1500"),   # obs max 981
    ("chargesObject", "Tax"):                  Decimal("200"),    # obs max 80
    ("chargesObject", "ShippingCharge"):       Decimal("200"),    # obs max 79
    ("chargesObject", "ShippingTax"):          Decimal("20"),     # obs max 8
    ("chargesObject", "Promotion"):            Decimal("60"),     # decision-E residual
    ("chargesObject", "GiftWrap"):             Decimal("5"),      # matches to cent
    ("chargesObject", "GiftWrapTax"):          Decimal("5"),
    ("chargesObject", "Shipping"):             Decimal("200"),    # Sellerise-only line
    # feesObject
    ("feesObject", "Commission"):              Decimal("300"),    # obs max 149
    ("feesObject", "ShippingChargeback"):      Decimal("120"),    # obs max 79
    ("feesObject", "GiftwrapChargeback"):      Decimal("5"),
    ("feesObject", "ReferralFee"):             Decimal("5"),      # decision A: 0 settled
    ("feesObject", "POAServiceFee"):           Decimal("5"),      # Sellerise-only
    ("feesObject", "PoAPerUnitFulfillmentFee"): Decimal("15"),    # Sellerise-only
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
    ("refundsObject", "RestockingFee"):        Decimal("5"),      # decision D — matches
    ("refundsObject", "Goodwill"):             Decimal("5"),      # decision D — matches
    # scalars / derived
    ("storageFee", "(scalar)"):                Decimal("5"),      # matches to cent
    ("salesTaxes", "(derived)"):               Decimal("250"),    # sum of tax lines
    # cog: Jan pre-backfill boundary = $2019 (structural, documented); we
    # accept up to $2500 for settled to accommodate that documented residual.
    # If we ever extend the backfill and it collapses, this band should tighten.
    ("cog", "(scalar)"):                       Decimal("2500"),
}

# Ad-line bands (per line, per month). Ad drift is sub-dollar to few-dollar per
# line (max observed $5.75 on May TOTAL). Widen to $10 per line, $30 for TOTAL,
# to allow for further restatement between pulls.
AD_LINE_BAND    = Decimal("10")
AD_TOTAL_BAND   = Decimal("30")

# Net formula sum can amplify per-bucket bands; the net-line band accepts up
# to the sum of the bucket bands touching it, capped.
NET_BAND        = Decimal("5000")

# The trailing month is still moving (refund lag, DEFERRED estimates). Widen
# bands by this factor for the trailing month only.
TRAILING_MULTIPLIER = Decimal("3")


def band_for(bucket: str, sub_line: str, is_trailing: bool) -> Decimal:
    """Return the drift band for one cell, adjusting for trailing regime."""
    base = SETTLED_BANDS.get((bucket, sub_line))
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
PRIOR_PULL_BANDS: dict[tuple[str, str], Decimal] = {
    # Match-to-cent cells — any movement between pulls is a signal, not noise
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
    # Small refunds sub-lines
    ("refundsObject", "ShippingTax"):          Decimal("1"),
    # Medium — small day-to-day restatements possible, catch anything larger
    ("chargesObject", "ShippingTax"):          Decimal("5"),
    ("chargesObject", "Promotion"):            Decimal("5"),
    ("feesObject", "ShippingChargeback"):      Decimal("10"),
    ("refundsObject", "RefundCommission"):     Decimal("5"),
    ("refundsObject", "Promotion"):            Decimal("5"),
    ("refundsObject", "Tax"):                  Decimal("10"),
    ("refundsObject", "Tax Withheld"):         Decimal("10"),
    ("refundsObject", "ShippingCharge"):       Decimal("5"),
    ("refundsObject", "ShippingChargeback"):   Decimal("5"),
    # Large aggregates — allow modest movement for genuine restatement, but
    # anything bigger than a small fraction of monthly total is a signal.
    ("chargesObject", "Principal"):            Decimal("100"),
    ("chargesObject", "Tax"):                  Decimal("30"),
    ("chargesObject", "ShippingCharge"):       Decimal("20"),
    ("chargesObject", "Shipping"):             Decimal("10"),
    ("feesObject", "Commission"):              Decimal("50"),
    ("fbaObject", "FBAPerUnitFulfillmentFee"): Decimal("50"),
    ("refundsObject", "Principal"):            Decimal("50"),
    ("refundsObject", "Commission"):           Decimal("20"),
    # Derived (net, salesTaxes) sum many cells — allow larger drift
    ("cog", "(scalar)"):                       Decimal("100"),
    ("salesTaxes", "(derived)"):               Decimal("30"),
    # net band chosen to still catch a ~$2.8k cog regression (the acceptance
    # test) — much tighter than the vs-Sellerise net band ($5,000).
    ("net", "(derived)"):                      Decimal("500"),
}

# Ad-side vs-prior-pull bands
PRIOR_PULL_AD_LINE_BAND  = Decimal("3")
PRIOR_PULL_AD_TOTAL_BAND = Decimal("10")

# Default for cells not listed
PRIOR_PULL_DEFAULT_BAND = Decimal("20")


def prior_pull_band_for(bucket: str, sub_line: str, is_trailing: bool) -> Decimal:
    """Return the vs-prior-pull drift band for one cell, trailing-aware."""
    base = PRIOR_PULL_BANDS.get((bucket, sub_line), PRIOR_PULL_DEFAULT_BAND)
    if is_trailing:
        return base * TRAILING_MULTIPLIER
    return base
