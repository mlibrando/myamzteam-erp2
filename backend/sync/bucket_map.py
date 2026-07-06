"""BUCKET_MAP — maps (txn_type, breakdown_type, txn_status) → BucketRule.

Each leaf resolves to (bucket, sub_line, inclusion), where:
- bucket    = Sellerise top-level bucket name ("chargesObject", "feesObject",
              "fbaObject", "refundsObject", "storageFee", "expenses",
              "passthrough")
- sub_line  = Sellerise sub-line under that bucket (e.g. "Principal",
              "Commission", "FBAPerUnitFulfillmentFee"). For expenses /
              passthrough the sub_line is "{txn_type}.{breakdown_type}" so
              individual leaves stay auditable.
- inclusion = "net"  → goes into Sellerise's net calculation
              "expenses" → real cost but excluded from Sellerise's net
              "passthrough" → wash-out lines (MFT, VAT, ads billed, etc.)

Rules are resolved with FIXED PRECEDENCE (decision G in RECONCILIATION.md):
1. passthrough leaves (MFT / VAT / LowValueGoodsTax / ProductAdsPayment.*)
2. explicit net leaves (chargesObject / feesObject / fbaObject / refundsObject
   / storageFee), including the status split from decision A
3. everything else → expenses (mirrors Sellerise's own catch-all)

A leaf missing from every rule surfaces as an UNMAPPED WARNING and defaults to
`expenses` so it stays out of net until we classify it.

References:
- reference/data/probe_breakdowns.md — full leaf inventory
- reference/data/SELLERISE_RAW_DATA.json — bucket-shape ground truth
- RECONCILIATION.md — Step 2 decisions A–G
"""

from __future__ import annotations

from dataclasses import dataclass

# ── inclusion flags ─────────────────────────────────────────────────────────

NET = "net"
EXPENSES = "expenses"
PASSTHROUGH = "passthrough"

# ── Sellerise bucket names ──────────────────────────────────────────────────

CHARGES = "chargesObject"
FEES = "feesObject"
FBA = "fbaObject"
REFUNDS = "refundsObject"
STORAGE = "storageFee"

# ── status categorization (decision A) ──────────────────────────────────────
# RELEASED + DEFERRED_RELEASED are both SETTLED money. DEFERRED alone is the
# unsettled estimate. Compare case-insensitively (Amazon sometimes returns
# "Released" instead of "RELEASED"; see Gotchas).

SETTLED_STATUSES: frozenset[str] = frozenset({"RELEASED", "DEFERRED_RELEASED"})
ESTIMATE_STATUSES: frozenset[str] = frozenset({"DEFERRED"})


def _norm_status(status: str | None) -> str:
    return (status or "").upper()


def is_settled(status: str | None) -> bool:
    return _norm_status(status) in SETTLED_STATUSES


def is_estimate(status: str | None) -> bool:
    return _norm_status(status) in ESTIMATE_STATUSES


@dataclass(frozen=True)
class BucketRule:
    bucket: str
    sub_line: str
    inclusion: str


# ── passthrough leaves (decision F + B) ─────────────────────────────────────
# Resolved FIRST — MFT/VAT are collect-and-remit (net-zero to profit) and have
# no Sellerise home; ProductAdsPayment.AdvertisingFee duplicates Ads-API spend.

_PASSTHROUGH_BREAKDOWN_TYPES: frozenset[str] = frozenset({
    # Marketplace-facilitator tax pass-throughs on Shipment
    "MarketplaceFacilitatorTax-Principal",
    "MarketplaceFacilitatorTax-Shipping",
    "MarketplaceFacilitatorTax-Other",
    "MarketplaceFacilitatorVAT-Principal",
    "MarketplaceFacilitatorVAT-Shipping",
    "LowValueGoodsTax-Principal",
    "LowValueGoodsTax-Shipping",
})

# Refund-side MFT variants route to refundsObject."Tax Withheld", not passthrough.
_REFUND_TAX_WITHHELD_TYPES: frozenset[str] = frozenset({
    "MarketplaceFacilitatorTax-Principal",
    "MarketplaceFacilitatorTax-Shipping",
    "MarketplaceFacilitatorTax-Other",
    "LowValueGoodsTax-Principal",
})

# ── net-mapping rules keyed on (txn_type, breakdown_type) ───────────────────
# Status split (decision A) is applied ON TOP of these for fee/FBA lines below.
# Anything not matched here falls through to expenses.

_SHIPMENT_CHARGES: dict[str, str] = {
    "OurPricePrincipal":  "Principal",
    "ProductCharges":     "Principal",     # txn-level fallback for "Principal"
    "OurPriceTax":        "Tax",
    "OurPriceDiscount":   "Promotion",
    "ShippingDiscount":   "Promotion",
    "ShippingPrincipal":  "ShippingCharge",
    "ShippingTax":        "ShippingTax",
    "GiftwrapPrincipal":  "GiftWrap",
    "GiftwrapTax":        "GiftWrapTax",
}

_SHIPMENT_FEE_STATIC: dict[str, str] = {
    "ShippingChargeback":  "ShippingChargeback",
    "GiftwrapChargeback":  "GiftwrapChargeback",
}

# Decision A + C — split by status. RELEASED/DEFERRED_RELEASED → settled bucket;
# DEFERRED → estimate bucket. AmazonFees/FBAFees are the txn-level parent
# fallbacks the flattener emits when items[] gives only "Base" roots (decision C).
_SHIPMENT_FEE_SETTLED: dict[str, str] = {
    "Commission":                "Commission",
    "AmazonFees":                "Commission",       # txn-level fallback → Commission
}
_SHIPMENT_FEE_ESTIMATE: dict[str, str] = {
    "Commission":                "ReferralFee",
    "AmazonFees":                "ReferralFee",
}
_SHIPMENT_FBA_SETTLED: dict[str, str] = {
    "FBAPerUnitFulfillmentFee":  "FBAPerUnitFulfillmentFee",
    "FBAFees":                   "FBAPerUnitFulfillmentFee",  # txn-level fallback
}
_SHIPMENT_FBA_ESTIMATE: dict[str, str] = {
    "FBAPerUnitFulfillmentFee":  "FBAFees",
    "FBAFees":                   "FBAFees",
}

# Refund → refundsObject sub-lines. All statuses treated identically.
_REFUND_LINES: dict[str, str] = {
    "OurPricePrincipal":            "Principal",
    "OurPriceTax":                  "Tax",
    "Commission":                   "Commission",
    "RefundCommission":             "RefundCommission",
    "OurPriceDiscount":             "Promotion",
    "ShippingDiscount":             "Promotion",
    "ShippingPrincipal":            "ShippingCharge",
    "ShippingTax":                  "ShippingTax",
    "ShippingChargeback":           "ShippingChargeback",
    "GiftwrapPrincipal":            "GiftWrap",
    "GiftwrapTax":                  "GiftWrapTax",
    "GiftwrapChargeback":           "GiftwrapChargeback",
    # Decision D
    "RestockingDeductionPrincipal": "RestockingFee",
    "RestockingDeductionTax":       "RestockingFee",
    "GoodwillPrincipal":            "Goodwill",
}

# Wrapper nodes the flattener emits with amount=0. Skip and count separately.
_KNOWN_ZERO_TYPES: frozenset[str] = frozenset({
    "Sales", "Expenses", "Refunded Sales", "Refunded Expenses",
})


# ── public API ──────────────────────────────────────────────────────────────

def classify(
    txn_type: str,
    breakdown_type: str,
    txn_status: str | None,
) -> BucketRule | None:
    """Return a BucketRule for one leaf, or None if it's a known zero-wrapper.

    Precedence order (decision G):
      1. passthrough
      2. explicit net rules (with status split for fees/FBA)
      3. expenses (catch-all)

    A leaf that reaches step 3 is a REAL leaf that just isn't a net bucket
    (e.g. FBALongTermStorageFee, FBAInventoryReimbursement) — it belongs in
    expenses. The aggregator flags leaves not present in this file at all as
    UNMAPPED (they also default to expenses, but with a warning).
    """
    if breakdown_type in _KNOWN_ZERO_TYPES:
        return None

    # 1. Passthrough (decisions B, F). MFT on refunds goes to refundsObject
    #    "Tax Withheld" — override the general passthrough classification.
    if txn_type == "Refund" and breakdown_type in _REFUND_TAX_WITHHELD_TYPES:
        return BucketRule(REFUNDS, "Tax Withheld", NET)

    if breakdown_type in _PASSTHROUGH_BREAKDOWN_TYPES:
        return BucketRule(PASSTHROUGH, f"{txn_type}.{breakdown_type}", PASSTHROUGH)

    if txn_type == "ProductAdsPayment" and breakdown_type in ("AdvertisingFee", "AdvertisingFeeRefund"):
        return BucketRule(PASSTHROUGH, f"ProductAdsPayment.{breakdown_type}", PASSTHROUGH)

    # Decision E — Shipment.Promo has no home in the Sellerise net taxonomy.
    # Sellerise builds refundsObject.Promotion from Refund.{OurPrice,Shipping}Discount
    # exactly; routing Promo into refundsObject.Promotion overshoots by the Promo
    # amount, and chargesObject.Promotion would inflate revenue. Track as audit only.
    if txn_type == "Shipment" and breakdown_type == "Promo":
        return BucketRule(PASSTHROUGH, "Shipment.Promo", PASSTHROUGH)

    # 2. Explicit net rules
    if txn_type == "Shipment":
        if breakdown_type in _SHIPMENT_CHARGES:
            return BucketRule(CHARGES, _SHIPMENT_CHARGES[breakdown_type], NET)

        if breakdown_type in _SHIPMENT_FEE_STATIC:
            return BucketRule(FEES, _SHIPMENT_FEE_STATIC[breakdown_type], NET)

        if breakdown_type in _SHIPMENT_FEE_SETTLED:
            sub = (_SHIPMENT_FEE_SETTLED if is_settled(txn_status)
                   else _SHIPMENT_FEE_ESTIMATE)[breakdown_type]
            return BucketRule(FEES, sub, NET)

        if breakdown_type in _SHIPMENT_FBA_SETTLED:
            sub = (_SHIPMENT_FBA_SETTLED if is_settled(txn_status)
                   else _SHIPMENT_FBA_ESTIMATE)[breakdown_type]
            return BucketRule(FBA, sub, NET)

    if txn_type == "Refund" and breakdown_type in _REFUND_LINES:
        return BucketRule(REFUNDS, _REFUND_LINES[breakdown_type], NET)

    if txn_type == "ServiceFee" and breakdown_type == "FBAStorageFee":
        return BucketRule(STORAGE, "storageFee", NET)

    # 3. Catch-all — real leaf, real cost, but excluded from net (decision G).
    return BucketRule(EXPENSES, f"{txn_type}.{breakdown_type}", EXPENSES)


__all__ = [
    "BucketRule",
    "NET", "EXPENSES", "PASSTHROUGH",
    "CHARGES", "FEES", "FBA", "REFUNDS", "STORAGE",
    "SETTLED_STATUSES", "ESTIMATE_STATUSES",
    "is_settled", "is_estimate",
    "classify",
]
