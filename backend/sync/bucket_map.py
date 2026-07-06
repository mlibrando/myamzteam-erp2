"""BUCKET_MAP — maps (transaction_type, breakdown_type) → (line_key, line_label, bucket).

line_key uses dotted paths that mirror the Sellerise sheet row structure.
bucket = the top-level P&L section (matches row headers in the sheet).

Any (txn_type, breakdown_type) pair not in this map is routed to
unmapped_breakdown_types by aggregate.py — nothing is silently dropped.

Types intentionally excluded (not P&L lines):
  - Transfer / FundTransfer  — bank settlement, not revenue
  - */Expenses, */Sales, */Refunded*  — zero-amount wrapper nodes
  - Adjustment / ReserveCredit + ReserveDebit  — cancel out exactly
"""

from __future__ import annotations

# (transaction_type, breakdown_type) → (line_key, line_label, bucket)
BUCKET_MAP: dict[tuple[str, str], tuple[str, str, str]] = {

    # ── SHIPMENT — regular sales ──────────────────────────────────────────
    ("Shipment", "OurPricePrincipal"):                    ("sales.product_sales",         "Product sales",                "Sales"),
    ("Shipment", "ProductCharges"):                       ("sales.product_sales",         "Product sales",                "Sales"),
    ("Shipment", "OurPriceTax"):                          ("sales.tax",                   "Tax",                          "Sales"),
    ("Shipment", "OurPriceDiscount"):                     ("sales.promotion",             "Promotion",                    "Sales"),
    ("Shipment", "ShippingDiscount"):                     ("sales.promotion",             "Promotion",                    "Sales"),
    ("Shipment", "Promo"):                                ("sales.promotion",             "Promotion",                    "Sales"),
    ("Shipment", "ShippingPrincipal"):                    ("sales.shipping_charge",       "Shipping charge",              "Sales"),
    ("Shipment", "ShippingTax"):                          ("sales.shipping_tax",          "Shipping tax",                 "Sales"),
    ("Shipment", "MarketplaceFacilitatorTax-Shipping"):   ("sales.shipping_tax",          "Shipping tax",                 "Sales"),
    ("Shipment", "GiftwrapPrincipal"):                    ("sales.gift_wrap",             "Gift wrap",                    "Sales"),
    ("Shipment", "GiftwrapTax"):                          ("sales.gift_wrap_tax",         "Gift wrap tax",                "Sales"),
    # MFT taxes (Amazon withholds and remits) → Taxes row (row 12)
    ("Shipment", "MarketplaceFacilitatorTax-Principal"):  ("taxes.mft",                   "Taxes",                        "Taxes"),
    ("Shipment", "MarketplaceFacilitatorTax-Other"):      ("taxes.mft",                   "Taxes",                        "Taxes"),
    ("Shipment", "MarketplaceFacilitatorVAT-Principal"):  ("taxes.mft",                   "Taxes",                        "Taxes"),
    ("Shipment", "MarketplaceFacilitatorVAT-Shipping"):   ("taxes.mft",                   "Taxes",                        "Taxes"),
    ("Shipment", "LowValueGoodsTax-Principal"):           ("taxes.mft",                   "Taxes",                        "Taxes"),
    ("Shipment", "LowValueGoodsTax-Shipping"):            ("taxes.mft",                   "Taxes",                        "Taxes"),
    # FBA fees
    ("Shipment", "FBAPerUnitFulfillmentFee"):             ("fba.per_unit",                "Fba per unit fulfillment fee", "FBA fees"),
    ("Shipment", "FBAFees"):                              ("fba.per_unit",                "Fba per unit fulfillment fee", "FBA fees"),
    # Referral fees
    ("Shipment", "Commission"):                           ("referral.commission",         "Commission",                   "Referral fees"),
    ("Shipment", "ShippingChargeback"):                   ("referral.shipping_chargeback","Shipping chargeback",          "Referral fees"),
    ("Shipment", "GiftwrapChargeback"):                   ("referral.giftwrap_chargeback","Giftwrap chargeback",          "Referral fees"),
    # Misc small Shipment types
    ("Shipment", "AmazonFees"):                           ("other_amz.amazon_fees",       "Amazon fees",                  "Other AMZ transactions"),
    ("Shipment", "BaseTax"):                              ("taxes.mft",                   "Taxes",                        "Taxes"),

    # ── REFUND ────────────────────────────────────────────────────────────
    ("Refund", "OurPricePrincipal"):                      ("refunds.product_sales",       "Product sales",                "Refunds"),
    ("Refund", "OurPriceTax"):                            ("refunds.tax",                 "Tax",                          "Refunds"),
    ("Refund", "MarketplaceFacilitatorTax-Principal"):    ("refunds.tax_withheld",        "Tax withheld",                 "Refunds"),
    ("Refund", "MarketplaceFacilitatorTax-Shipping"):     ("refunds.tax_withheld",        "Tax withheld",                 "Refunds"),
    ("Refund", "MarketplaceFacilitatorTax-Other"):        ("refunds.tax_withheld",        "Tax withheld",                 "Refunds"),
    ("Refund", "LowValueGoodsTax-Principal"):             ("refunds.tax",                 "Tax",                          "Refunds"),
    ("Refund", "Commission"):                             ("refunds.commission",          "Commission",                   "Refunds"),
    ("Refund", "RefundCommission"):                       ("refunds.refund_commission",   "Refund commission",            "Refunds"),
    ("Refund", "ShippingPrincipal"):                      ("refunds.shipping_charge",     "Shipping charge",              "Refunds"),
    ("Refund", "ShippingChargeback"):                     ("refunds.shipping_chargeback", "Shipping chargeback",          "Refunds"),
    ("Refund", "ShippingDiscount"):                       ("refunds.promotion",           "Promotion",                    "Refunds"),
    ("Refund", "OurPriceDiscount"):                       ("refunds.promotion",           "Promotion",                    "Refunds"),
    ("Refund", "ShippingTax"):                            ("refunds.shipping_tax",        "Shipping tax",                 "Refunds"),
    ("Refund", "GiftwrapPrincipal"):                      ("refunds.gift_wrap",           "Gift wrap",                    "Refunds"),
    ("Refund", "GiftwrapTax"):                            ("refunds.gift_wrap_tax",       "Gift wrap tax",                "Refunds"),
    ("Refund", "GiftwrapChargeback"):                     ("refunds.giftwrap_chargeback", "Giftwrap chargeback",          "Refunds"),
    ("Refund", "RestockingDeductionPrincipal"):           ("refunds.restocking_fee",      "Restocking fee",               "Refunds"),
    ("Refund", "RestockingDeductionTax"):                 ("refunds.restocking_fee",      "Restocking fee",               "Refunds"),
    ("Refund", "GoodwillPrincipal"):                      ("refunds.goodwill",            "Goodwill",                     "Refunds"),

    # ── SERVICE FEE — Amazon-billed charges ──────────────────────────────
    ("ServiceFee", "FBAStorageFee"):                      ("storage.monthly",             "Storage fees",                 "Storage fees"),
    ("ServiceFee", "FBALongTermStorageFee"):              ("other_amz.storage_renewal",   "Storage renewal billing",      "Other AMZ transactions"),
    ("ServiceFee", "FBAInboundTransportationFee"):        ("other_amz.inbound_transport", "Inbound transportation fee",   "Other AMZ transactions"),
    ("ServiceFee", "FBAInboundConvenienceFee"):           ("other_amz.inbound_placement", "Fba inbound placement service fee", "Other AMZ transactions"),
    ("ServiceFee", "FBARemovalFee"):                      ("other_amz.removal_complete",  "Removal complete",             "Other AMZ transactions"),
    ("ServiceFee", "FBADisposalFee"):                     ("other_amz.disposal_complete", "Disposal complete",            "Other AMZ transactions"),
    ("ServiceFee", "PaidServicesFee"):                    ("other_amz.premium_services",  "Premium services fee",         "Other AMZ transactions"),
    ("ServiceFee", "Subscription"):                       ("other_amz.subscription",      "Subscription fee",             "Other AMZ transactions"),
    ("ServiceFee", "CouponPerformanceFee"):               ("other_amz.amazon_fees",       "Amazon fees",                  "Other AMZ transactions"),
    ("ServiceFee", "CouponParticipationFee"):             ("other_amz.amazon_fees",       "Amazon fees",                  "Other AMZ transactions"),
    ("ServiceFee", "CustomerReturnHRRUnitFee"):           ("other_amz.amazon_fees",       "Amazon fees",                  "Other AMZ transactions"),
    ("ServiceFee", "Tax"):                                ("taxes.mft",                   "Taxes",                        "Taxes"),

    # ── FBA INVENTORY REIMBURSEMENT ──────────────────────────────────────
    # Both positive (reimbursements) and negative (reversed reimbursements / clawbacks)
    # roll into the same section in the sheet. Sub-type detail is not available from
    # the API at the breakdown level (it's a single FBAInventoryReimbursement type).
    ("FBAInventoryReimbursement", "FBAInventoryReimbursement"): ("other_amz.reversal_reimbursement", "Reversal reimbursement", "Other AMZ transactions"),
    ("FBAInventoryReimbursement", "FBAReversedReimbursement"):  ("other_amz.compensated_clawback",   "Compensated clawback",   "Other AMZ transactions"),

    # ── REMOVAL SHIPMENT — liquidations ──────────────────────────────────
    ("RemovalShipment", "RecommerceLiquidation"):         ("other_amz.liquidations",      "Liquidations",                 "Other AMZ transactions"),
    ("RemovalShipment", "AmazonFees"):                    ("other_amz.removal_complete",  "Removal complete",             "Other AMZ transactions"),
    ("RemovalShipment", "TaxOnRevenue"):                  ("taxes.mft",                   "Taxes",                        "Taxes"),
    ("RemovalShipment", "MarketplaceFacilitatorTax-Principal"): ("taxes.mft",             "Taxes",                        "Taxes"),

    # ── PRODUCT ADS PAYMENT — advertising fees billed through SP-API ─────
    # Note: detailed ad spend per product type comes from Phase 4 (Ads API).
    # These entries are the billing summaries that appear in financial statements.
    ("ProductAdsPayment", "AdvertisingFee"):              ("advertising.advertising_fee", "Advertising fee",              "Advertising expenses"),
    ("ProductAdsPayment", "AdvertisingFeeRefund"):        ("advertising.advertising_fee", "Advertising fee",              "Advertising expenses"),

    # ── ADJUSTMENT — reserves cancel out, tiny misc ───────────────────────
    # ReserveCredit / ReserveDebit cancel to zero — keep them so pnl_monthly
    # reflects the gross amounts (useful for period-matching validation).
    ("Adjustment", "AmazonFees"):                         ("other_amz.amazon_fees",       "Amazon fees",                  "Other AMZ transactions"),
    ("Adjustment", "RecommerceLiquidation"):              ("other_amz.liquidations",      "Liquidations",                 "Other AMZ transactions"),
    ("Adjustment", "MarketplaceFacilitatorTax-Principal"):("taxes.mft",                   "Taxes",                        "Taxes"),
    ("Adjustment", "Tax"):                                ("taxes.mft",                   "Taxes",                        "Taxes"),

    # ── RETROCHARGE ───────────────────────────────────────────────────────
    ("Retrocharge", "BaseTax"):                           ("other_amz.retrocharge",       "Retrocharge",                  "Other AMZ transactions"),
    ("Retrocharge", "MarketplaceFacilitatorTax-Principal"):("taxes.mft",                  "Taxes",                        "Taxes"),
    ("Retrocharge", "Other"):                             ("other_amz.retrocharge_reversal", "Retrocharge reversal",      "Other AMZ transactions"),
    ("Retrocharge", "RetrochargeReversal"):               ("other_amz.retrocharge_reversal", "Retrocharge reversal",      "Other AMZ transactions"),
    ("Retrocharge", "ShippingTax"):                       ("sales.shipping_tax",          "Shipping tax",                 "Sales"),

    # ── MISC LEDGER ADJUSTMENT ────────────────────────────────────────────
    ("MiscellaneousLedgerAdjustment", "Other"):           ("other_amz.fee_adjustment",    "Fee adjustment",               "Other AMZ transactions"),

    # ── INTENTIONALLY EXCLUDED (not P&L lines) ───────────────────────────
    # Transfer / FundTransfer: bank settlement disbursements
    # */Expenses, */Sales, */Refunded*: zero-amount wrapper nodes emitted by
    #   breakdown_leaves_for_txn for no-item / txn-level fallback transactions
    # Adjustment / ReserveCredit + ReserveDebit: offset each other perfectly
}

# Zero-amount wrapper types that appear from transaction-level fallback — always zero,
# never need to be in pnl_monthly but also shouldn't be flagged as unmapped.
KNOWN_ZERO_TYPES: frozenset[str] = frozenset({
    "Sales", "Expenses", "Refunded Sales", "Refunded Expenses",
    "FundTransfer",         # Transfer txns — bank disbursement, not P&L
    "ReserveCredit",        # Adjustment — offset by ReserveDebit
    "ReserveDebit",         # Adjustment — offset by ReserveCredit
})
