"""Sellerboard AU target adapter.

AU reconciles against Sellerboard rather than Sellerise. Same Amazon source
data, different target tool, and three currency facts that make a naive
comparison silently wrong by 30-50%:

  * SP-API AU transactions are **AUD** (native-currency pipeline invariant).
  * Sellerboard reports **USD** (its account currency).
  * The AU COGS workbook sheet's cost column is **USD**, even though its retail
    column is AUD. See `MARKETPLACE_COG_CURRENCY` in config.py.

FX lives here and nowhere else. The pipeline stays native AUD; this module
converts Sellerboard USD -> AUD so both sides meet in AUD.

Two Sellerboard-vs-us structural differences, both verified against the file
(`reference/data/au_sellerboard_reconcile.md` carries the arithmetic):

1. **Sign convention is inverted.** Sellerboard's cost fields are already
   negative and `netProfit` is built by *adding* them. Sellerise subtracts
   positive magnitudes. `map_to_buckets` re-signs to our convention.

2. **Amazon fees are GST-inclusive.** Sellerboard's "FBA per unit fulfilment
   fee", "FBA storage fee" and `advertising` carry AU's 10% GST. Our pipeline
   splits GST off into a bare `Tax` leaf that `bucket_map.classify()` routes to
   passthrough, so our fee buckets are GST-*exclusive*. Comparing them without
   normalising makes the implied FX rate look ~10% too high on exactly those
   lines. The referral fee carries no GST and needs no adjustment.

Net basis: Sellerboard's `netProfit` uses **`productCosts`** (gross COGS,
including inventory losses), NOT `salesCosts`. Verified to the cent across all
six months by `assert_net_reproduces`. `salesCosts` overshoots by exactly
`costOfMissingReturns + missingFromInboundCosts` each month; that is the
quantity our `listTransactions`-derived cog cannot see, so our cog matches
`salesCosts`, not `productCosts`.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import statistics
from decimal import Decimal
from typing import Any

from .config import MARKETPLACE_ALIASES

AU_MARKETPLACE_ID = MARKETPLACE_ALIASES["AU"]

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SELLERBOARD_JSON = _REPO_ROOT / "reference" / "data" / "SELLERBOARD_RAW_DATA.json"

# AU GST. Verified empirically at 9.99%-10.01% every month against two
# independent leaves (Shipment.Tax over FBA+ShippingChargeback, and
# ServiceFee.Tax over storage+disposal+long-term). Applied to put our
# GST-exclusive fee buckets onto Sellerboard's GST-inclusive basis.
GST_RATE = Decimal("0.10")
GST_GROSS_UP = Decimal("1") + GST_RATE

# Sellerboard `amazonFees[].name` -> (our bucket, our sub_line, gst_inclusive).
# `gst_inclusive` records whether Sellerboard's figure already contains GST,
# which determines whether our side needs grossing up before comparison.
FEE_NAME_MAP: dict[str, tuple[str, str, bool]] = {
    "Referral fee":                  ("feesObject", "Commission",               False),
    "FBA per unit fulfilment fee":   ("fbaObject",  "FBAPerUnitFulfillmentFee", True),
    "FBA storage fee":               ("storageFee", "storageFee",               True),
    "Long term storage fee":         ("expenses",   "ServiceFee.FBALongTermStorageFee", True),
    "FBA disposal fee":              ("expenses",   "ServiceFee.FBADisposalFee", True),
    "Subscription":                  ("expenses",   "ServiceFee.Subscription",  False),
    # Positive credits. Our pipeline books these under FBAInventoryReimbursement
    # (expenses, excluded from Sellerise-style net); Sellerboard folds them into
    # `amazonFeesTotal`, which *is* in its net.
    "Reversal reimbursement":        ("expenses",   "FBAInventoryReimbursement.Reversal", False),
    "Warehouse damage":              ("expenses",   "FBAInventoryReimbursement.WarehouseDamage", False),
    "Free replacement refund items": ("expenses",   "FBAInventoryReimbursement.FreeReplacement", False),
}

# Sellerboard `refundCosts[].name` -> (our bucket, sub_line).
#
# `cogAdjust` is deliberately its own bucket rather than folded into `cog`:
# these two lines are *components of* `refundCostsTotal`, so summing them into
# cog would double-count them against the refund bucket. Keeping them separate
# lets `assert_bucket_totals` prove nothing was lost or counted twice.
REFUND_NAME_MAP: dict[str, tuple[str, str]] = {
    "Refunded amount":           ("refundsObject", "Principal"),
    "Refund commission":         ("refundsObject", "RefundCommission"),
    "Refunded referral fee":     ("refundsObject", "Commission"),
    "Refunded shipping":         ("refundsObject", "ShippingCharge"),
    "Shipping tax":              ("refundsObject", "ShippingTax"),
    "Promotion":                 ("refundsObject", "Promotion"),
    "Ship Promotion":            ("refundsObject", "Promotion"),
    "LowValueGoodsTax-Principal": ("refundsObject", "Tax Withheld"),
    "ShippingTaxDiscount":       ("refundsObject", "ShippingTaxDiscount"),
    # COGS-side recoveries, not refund cash. `Value of returned items` is the cog
    # of sellable returns; `Unsellable products costs` is inventory written off.
    "Value of returned items":   ("cogAdjust",     "ReturnedItemsValue"),
    "Unsellable products costs": ("cogAdjust",     "UnsellableProducts"),
}

# Sellerboard fields with no home in our schema. Surfaced rather than dropped.
UNMAPPED_SELLERBOARD_FIELDS = (
    "missingFromInboundCosts",   # inventory lost inbound; invisible to listTransactions
    "costOfMissingReturns",      # returns never physically received
    "shippingCost",              # seller-fulfilled shipping (Shipping_FBA here)
    "vatTotal", "vatFacilitator", "vatCosts",  # all zero on this account
)


class SellerboardParseError(ValueError):
    pass


# ── parsing ────────────────────────────────────────────────────────────────

def _is_real_month(period: dict[str, Any]) -> bool:
    """Reject the leading `is_totals` summary and the trailing `preparing` stub.

    Ingesting either as a month corrupts every downstream aggregate: the totals
    row double-counts the whole period, and the stub is a partial month.
    """
    return (
        bool(period.get("has_data"))
        and not period.get("is_totals")
        and period.get("status") != "preparing"
    )


def _assert_calendar_month(period: dict[str, Any]) -> str:
    """Return 'YYYY-MM', raising if the period is not a whole calendar month.

    Sellerboard's `end` is the last *day* of the month at 00:00 UTC (Jan ends
    2026-01-31, not 2026-02-01), so we check start-is-first-day and
    end-is-last-day rather than a naive span.
    """
    start = dt.datetime.fromtimestamp(period["start"], tz=dt.timezone.utc)
    end = dt.datetime.fromtimestamp(period["end"], tz=dt.timezone.utc)
    if start.day != 1:
        raise SellerboardParseError(f"period does not start on the 1st: {start:%Y-%m-%d}")
    next_day = end + dt.timedelta(days=1)
    if next_day.month == end.month:
        raise SellerboardParseError(f"period does not end on the last day: {end:%Y-%m-%d}")
    if (start.year, start.month) != (end.year, end.month):
        raise SellerboardParseError(f"period spans months: {start:%Y-%m-%d}..{end:%Y-%m-%d}")
    return f"{start:%Y-%m}"


def load_sellerboard(path: pathlib.Path | None = None) -> dict[str, dict[str, Any]]:
    """Return {year_month: period} for the real, complete calendar months."""
    raw = json.loads((path or SELLERBOARD_JSON).read_text())
    months: dict[str, dict[str, Any]] = {}
    for period in raw:
        if not _is_real_month(period):
            continue
        months[_assert_calendar_month(period)] = period
    if not months:
        raise SellerboardParseError("no complete months found — check the junk-row filter")
    return dict(sorted(months.items()))


# ── net formula ────────────────────────────────────────────────────────────

def _d(period: dict[str, Any], key: str) -> Decimal:
    return Decimal(str(period.get(key) or 0))


def sellerboard_net(period: dict[str, Any]) -> Decimal:
    """Reproduce Sellerboard's `netProfit` from components.

    Every cost term is already negative, so the formula *adds* throughout.
    `productCosts` (not `salesCosts`) is the COGS term — proven by
    `assert_net_reproduces`.
    """
    return (
        _d(period, "sales")
        + _d(period, "amazonFeesTotal")
        + _d(period, "productCosts")
        + _d(period, "advertising")
        + _d(period, "refundCostsTotal")
        + _d(period, "shippingCost")
    )


def inventory_loss_gap(period: dict[str, Any]) -> Decimal:
    """`productCosts - salesCosts`: COGS for stock that never sold.

    Sellerboard deducts this in `netProfit`; our `listTransactions`-derived cog
    cannot see it. A named source-of-data difference, not drift.
    """
    return _d(period, "productCosts") - _d(period, "salesCosts")


def assert_net_reproduces(months: dict[str, dict[str, Any]], tolerance: Decimal = Decimal("0.01")) -> None:
    """Gate: our understanding of Sellerboard's net formula must be exact.

    Also asserts the `salesCosts` identity, so a future Sellerboard schema
    change that redefines either term fails loudly here rather than silently
    shifting AU's net.
    """
    for ym, period in months.items():
        got, want = sellerboard_net(period), _d(period, "netProfit")
        if abs(got - want) > tolerance:
            raise SellerboardParseError(
                f"{ym}: net formula does not reproduce netProfit "
                f"(got {got}, want {want}, delta {got - want}). "
                "productCosts is the COGS basis — check the schema."
            )
        identity = (
            _d(period, "salesCosts")
            - (_d(period, "productCosts")
               - _d(period, "costOfMissingReturns")
               - _d(period, "missingFromInboundCosts"))
        )
        if abs(identity) > tolerance:
            raise SellerboardParseError(
                f"{ym}: salesCosts != productCosts - costOfMissingReturns - "
                f"missingFromInboundCosts (off by {identity})"
            )


# ── bucket mapping (USD, our sign convention) ──────────────────────────────

def map_to_buckets(period: dict[str, Any]) -> dict[str, dict[str, Decimal]]:
    """Sellerboard month -> our {bucket: {sub_line: amount}} shape, in USD.

    Signs are flipped into our convention: revenue positive, fee/FBA/refund
    lines negative, storageFee and cog positive magnitudes.
    """
    out: dict[str, dict[str, Decimal]] = {}

    def put(bucket: str, sub: str, value: Decimal) -> None:
        out.setdefault(bucket, {})
        out[bucket][sub] = out[bucket].get(sub, Decimal("0")) + value

    # Sellerboard's `sales` is gross product + shipping revenue, not promo-netted.
    # It has no principal/shipping split, so it lands as one revenue line.
    put("chargesObject", "Revenue", _d(period, "sales"))

    # Sellerboard pads some `name` values with a trailing space ("Subscription ").
    for fee in period.get("amazonFees") or []:
        name = (fee.get("name") or "").strip()
        amount = Decimal(str(fee.get("amount") or 0))
        mapped = FEE_NAME_MAP.get(name)
        if mapped is None:
            put("expenses", f"UNMAPPED.amazonFees.{name}", amount)
            continue
        bucket, sub, _gst = mapped
        # storageFee is a positive magnitude in our schema; everything else keeps
        # Sellerboard's sign (already negative for costs, positive for credits).
        put(bucket, sub, -amount if bucket == "storageFee" else amount)

    for refund in period.get("refundCosts") or []:
        name = (refund.get("name") or "").strip()
        amount = Decimal(str(refund.get("amount") or 0))
        mapped = REFUND_NAME_MAP.get(name)
        if mapped is None:
            put("expenses", f"UNMAPPED.refundCosts.{name}", amount)
            continue
        bucket, sub = mapped
        put(bucket, sub, amount)

    # adExpenses is a positive magnitude in our schema; Sellerboard stores it negative.
    put("adExpenses", "(aggregate)", -_d(period, "advertising"))

    # cog: positive magnitude. `salesCosts` is the basis that matches our
    # net_units x unit_cog pipeline; `productCosts` additionally carries
    # inventory losses we cannot observe. Both are exposed so callers pick
    # explicitly rather than inheriting whichever happened to be first.
    put("cog", "(salesCosts)", -_d(period, "salesCosts"))
    put("cog", "(productCosts)", -_d(period, "productCosts"))

    put("expenses", "shippingCost", _d(period, "shippingCost"))
    return out


def assert_bucket_totals(months: dict[str, dict[str, Any]], tolerance: Decimal = Decimal("0.01")) -> None:
    """Prove `map_to_buckets` neither drops nor double-counts a Sellerboard line.

    `amazonFees[]` must sum to `amazonFeesTotal`, and `refundCosts[]` must sum to
    `refundCostsTotal`. Because the refund array is split across `refundsObject`
    and `cogAdjust`, the second check is what stops a future rename from quietly
    landing a cog line in the refund bucket (or vice versa).
    """
    for ym, period in months.items():
        fees = sum((Decimal(str(f.get("amount") or 0)) for f in period.get("amazonFees") or []),
                   start=Decimal("0"))
        if abs(fees - _d(period, "amazonFeesTotal")) > tolerance:
            raise SellerboardParseError(
                f"{ym}: amazonFees[] sums to {fees}, amazonFeesTotal is "
                f"{_d(period, 'amazonFeesTotal')}"
            )

        refunds = sum((Decimal(str(r.get("amount") or 0)) for r in period.get("refundCosts") or []),
                      start=Decimal("0"))
        if abs(refunds - _d(period, "refundCostsTotal")) > tolerance:
            raise SellerboardParseError(
                f"{ym}: refundCosts[] sums to {refunds}, refundCostsTotal is "
                f"{_d(period, 'refundCostsTotal')}"
            )

        buckets = map_to_buckets(period)
        mapped_refund_side = (
            sum(buckets.get("refundsObject", {}).values(), start=Decimal("0"))
            + sum(buckets.get("cogAdjust", {}).values(), start=Decimal("0"))
        )
        if abs(mapped_refund_side - _d(period, "refundCostsTotal")) > tolerance:
            raise SellerboardParseError(
                f"{ym}: refundsObject + cogAdjust = {mapped_refund_side} but "
                f"refundCostsTotal = {_d(period, 'refundCostsTotal')} — a refundCosts "
                "line is unmapped or double-counted"
            )


# ── implied FX ─────────────────────────────────────────────────────────────

class FxAnchor:
    """One (Sellerboard USD, ours AUD) pair whose quotient implies the rate.

    `gross_up` puts our GST-exclusive figure onto Sellerboard's GST-inclusive
    basis.

    `content_sensitive` marks anchors whose two sides can differ for reasons
    other than FX, so a bad rate and bad content are indistinguishable in them:

      * revenue / commission / FBA fee — contaminated by any shipment scope or
        cut-off difference (2026-01 has 9 units Sellerboard never counted).
      * storage fee — billed in arrears, so January's charge covers December's
        stored inventory and the two sides describe different periods.

    The insensitive anchors are refunds (both sides describe the identical
    refund events) and advertising (sourced from the Ads API, entirely outside
    the SP-API transaction set). Those are what we fall back to when the
    sensitive ones disagree.
    """

    def __init__(self, name: str, *, gross_up: bool = False, content_sensitive: bool = True):
        self.name = name
        self.gross_up = gross_up
        self.content_sensitive = content_sensitive

    def rate(self, usd: Decimal, aud: Decimal) -> Decimal | None:
        if not aud or not usd:
            return None
        denom = abs(aud) * (GST_GROSS_UP if self.gross_up else Decimal("1"))
        return abs(usd) / denom


FX_ANCHORS: tuple[FxAnchor, ...] = (
    FxAnchor("sales / Principal"),
    FxAnchor("ReferralFee / Commission"),
    FxAnchor("FBAfee / FBAPerUnitFulfillmentFee", gross_up=True),
    FxAnchor("Storage / FBAStorageFee", gross_up=True),
    FxAnchor("RefundedAmount / Refund.Principal", content_sensitive=False),
    FxAnchor("RefundedReferralFee / Refund.Commission", content_sensitive=False),
    FxAnchor("advertising / ad_spend_daily", gross_up=True, content_sensitive=False),
)

# Sellerboard converts at finer-than-monthly granularity: within a month, its
# refund lines agree with each other to four decimal places, its shipment lines
# agree with each other, and the two families land on *different* rates. So no
# single monthly rate is exact, and a monthly conversion always leaves a residual.
#
# FX_RATE_TOLERANCE bounds how far a family's own rate may sit from the reference
# rate and still be explicable as date-mix. It is deliberately an absolute rate
# tolerance, not a fitted spread: fitting the band to the observed disagreement
# would let any gap, however large, redefine itself as "expected FX". At 0.02
# (~2.8% relative) it comfortably covers real intra-month AUD/USD dispersion
# while still rejecting 2026-01's shipment family, which sits 0.09 below the
# reference — a move no currency makes inside one month.
FX_RATE_TOLERANCE = Decimal("0.02")

# Beyond this, a family's rate cannot be date-mix and the family is treated as
# content-contaminated when choosing the reference rate.
ANCHOR_SPREAD_WARN = Decimal("0.05")

# Sellerboard rounds every converted line to cents, so a bucket built from ~100
# transactions carries sub-dollar accumulated rounding. Without a floor the band
# scales to zero on small buckets and flags 32-cent differences as content.
FX_BAND_FLOOR_USD = Decimal("5.00")


def implied_rate(anchor_rates: dict[str, Decimal]) -> tuple[Decimal, Decimal]:
    """Consensus AUD->USD rate and the anchor spread, from GST-normalised anchors.

    Median, not mean: one contaminated anchor should not drag the rate. The
    spread is returned so callers can size the FX-granularity band -- Sellerboard
    converts at finer-than-monthly granularity, so a monthly rate always leaves
    a residual of roughly (bucket value x spread/2).
    """
    values = sorted(anchor_rates.values())
    if not values:
        raise SellerboardParseError("no usable FX anchors")
    median = Decimal(str(statistics.median([float(v) for v in values])))
    return median, values[-1] - values[0]


def fx_band(ours_aud: Decimal, tolerance: Decimal = FX_RATE_TOLERANCE) -> Decimal:
    """USD residual explicable by monthly-vs-daily rate granularity.

    A rate error of `tolerance` applied to `ours_aud` costs `ours_aud x tolerance`
    USD, so that is the widest residual FX alone can produce. Floored at the
    cent-rounding noise level. Note the band scales with our *AUD* figure, not
    the converted one — the rate is what is uncertain, not the underlying amount.
    """
    return max(abs(ours_aud) * tolerance, FX_BAND_FLOOR_USD)


def usd_to_aud(usd: Decimal, rate: Decimal) -> Decimal:
    """Convert a Sellerboard USD figure into pipeline-native AUD."""
    if not rate:
        raise SellerboardParseError("cannot convert at a zero rate")
    return usd / rate


__all__ = [
    "AU_MARKETPLACE_ID", "SELLERBOARD_JSON", "GST_RATE", "GST_GROSS_UP",
    "FEE_NAME_MAP", "REFUND_NAME_MAP", "UNMAPPED_SELLERBOARD_FIELDS",
    "SellerboardParseError", "load_sellerboard", "sellerboard_net",
    "inventory_loss_gap", "assert_net_reproduces", "assert_bucket_totals",
    "map_to_buckets",
    "FxAnchor", "FX_ANCHORS", "ANCHOR_SPREAD_WARN", "FX_BAND_FLOOR_USD",
    "FX_RATE_TOLERANCE", "implied_rate", "fx_band", "usd_to_aud",
]
