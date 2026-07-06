# Leaf breakdownType probe — marketplace ATVPDKIKX0DER

Source: sp_transactions.raw_json (excluding is_deferred_release_event=true).
Coverage: 13,818 transactions.

Grouped by (transactionType, transactionStatus). RELEASED = settled amounts;
DEFERRED = Amazon's estimate for orders not yet posted (see plan Ground Truth 2).

## Adjustment / DEFERRED_RELEASED

| breakdownType | occ. | currency | min | median | max |
|---|---:|---|---:|---:|---:|
| `AmazonFees` | 1 | USD | 0.65 | 0.65 | 0.65 |
| `RecommerceLiquidation` | 1 | USD | -0.31 | -0.31 | -0.31 |

## Adjustment / RELEASED

| breakdownType | occ. | currency | min | median | max |
|---|---:|---|---:|---:|---:|
| `MarketplaceFacilitatorTax-Principal` | 4 | USD | 0.04 | 0.04 | 0.04 |
| `Tax` | 4 | USD | -0.04 | -0.04 | -0.04 |
| `ReserveCredit` | 1 | USD | 17856.10 | 17856.10 | 17856.10 |
| `ReserveDebit` | 1 | USD | -17856.10 | -17856.10 | -17856.10 |

## FBAInventoryReimbursement / RELEASED

| breakdownType | occ. | currency | min | median | max |
|---|---:|---|---:|---:|---:|
| `FBAInventoryReimbursement` | 224 | USD | 0.31 | 42.88 | 817.00 |
| `FBAReversedReimbursement` | 61 | USD | -298.78 | -51.30 | -3.52 |

## MiscellaneousLedgerAdjustment / RELEASED

| breakdownType | occ. | currency | min | median | max |
|---|---:|---|---:|---:|---:|
| `Other` | 1 | USD | 0.74 | 0.74 | 0.74 |

## ProductAdsPayment / RELEASED

| breakdownType | occ. | currency | min | median | max |
|---|---:|---|---:|---:|---:|
| `AdvertisingFee` | 238 | USD | -544.68 | -503.18 | -73.91 |
| `Sales` | 238 | USD | 0.00 | 0.00 | 0.00 |
| `AdvertisingFeeRefund` | 1 | USD | 20.01 | 20.01 | 20.01 |
| `Expenses` | 1 | USD | 0.00 | 0.00 | 0.00 |

## Refund / DEFERRED

| breakdownType | occ. | currency | min | median | max |
|---|---:|---|---:|---:|---:|
| `Commission` | 3 | USD | 2.84 | 2.99 | 28.35 |
| `OurPricePrincipal` | 3 | USD | -189.00 | -19.95 | -19.95 |
| `RefundCommission` | 3 | USD | -5.00 | -0.60 | -0.57 |
| `MarketplaceFacilitatorTax-Principal` | 1 | USD | 14.65 | 14.65 | 14.65 |
| `OurPriceDiscount` | 1 | USD | 1.00 | 1.00 | 1.00 |
| `OurPriceTax` | 1 | USD | -14.65 | -14.65 | -14.65 |

## Refund / DEFERRED_RELEASED

| breakdownType | occ. | currency | min | median | max |
|---|---:|---|---:|---:|---:|
| `OurPricePrincipal` | 81 | USD | -224.45 | -48.50 | -19.95 |
| `Commission` | 80 | USD | 2.69 | 7.28 | 33.67 |
| `RefundCommission` | 80 | USD | -5.00 | -1.46 | -0.54 |
| `OurPriceTax` | 49 | USD | -18.52 | -10.14 | -0.20 |
| `MarketplaceFacilitatorTax-Principal` | 48 | USD | 0.20 | 10.35 | 18.52 |
| `ShippingPrincipal` | 10 | USD | -15.31 | -3.45 | -2.47 |
| `ShippingDiscount` | 6 | USD | 2.47 | 2.99 | 4.51 |
| `ShippingChargeback` | 4 | USD | 3.91 | 6.99 | 15.31 |
| `OurPriceDiscount` | 3 | USD | 1.00 | 1.00 | 2.00 |
| `MarketplaceFacilitatorTax-Shipping` | 2 | USD | 0.32 | 0.34 | 0.37 |
| `ShippingTax` | 2 | USD | -0.37 | -0.34 | -0.32 |

## Refund / RELEASED

| breakdownType | occ. | currency | min | median | max |
|---|---:|---|---:|---:|---:|
| `OurPricePrincipal` | 304 | USD | -302.95 | -142.52 | -16.17 |
| `Commission` | 299 | USD | 2.40 | 21.67 | 45.44 |
| `RefundCommission` | 299 | USD | -5.00 | -4.33 | -0.48 |
| `OurPriceTax` | 248 | USD | -28.35 | -11.27 | -0.20 |
| `MarketplaceFacilitatorTax-Principal` | 246 | USD | 0.20 | 11.27 | 23.57 |
| `ShippingPrincipal` | 47 | USD | -76.82 | -4.00 | -0.20 |
| `ShippingChargeback` | 24 | USD | 0.35 | 6.70 | 76.82 |
| `ShippingDiscount` | 23 | USD | 0.20 | 2.99 | 42.84 |
| `OurPriceDiscount` | 20 | USD | 1.00 | 16.73 | 34.49 |
| `MarketplaceFacilitatorTax-Shipping` | 14 | USD | 0.01 | 0.46 | 0.98 |
| `ShippingTax` | 14 | USD | -0.98 | -0.46 | -0.01 |
| `GoodwillPrincipal` | 4 | USD | -13.92 | -13.23 | -3.17 |
| `RestockingDeductionPrincipal` | 4 | USD | 4.59 | 15.32 | 31.99 |
| `Refunded Expenses` | 3 | USD | 0.00 | 0.00 | 0.00 |
| `Refunded Sales` | 3 | USD | 0.00 | 0.00 | 0.00 |
| `GiftwrapChargeback` | 1 | USD | 3.99 | 3.99 | 3.99 |
| `GiftwrapPrincipal` | 1 | USD | -3.99 | -3.99 | -3.99 |
| `GiftwrapTax` | 1 | USD | -0.32 | -0.32 | -0.32 |
| `LowValueGoodsTax-Principal` | 1 | USD | 28.35 | 28.35 | 28.35 |
| `MarketplaceFacilitatorTax-Other` | 1 | USD | 0.32 | 0.32 | 0.32 |
| `RestockingDeductionTax` | 1 | USD | 0.28 | 0.28 | 0.28 |

## RemovalShipment / DEFERRED

| breakdownType | occ. | currency | min | median | max |
|---|---:|---|---:|---:|---:|
| `AmazonFees` | 49 | USD | -0.93 | -0.47 | -0.47 |
| `RecommerceLiquidation` | 49 | USD | 0.83 | 0.83 | 2.17 |

## RemovalShipment / DEFERRED_RELEASED

| breakdownType | occ. | currency | min | median | max |
|---|---:|---|---:|---:|---:|
| `AmazonFees` | 1422 | USD | -5.14 | -0.65 | -0.27 |
| `RecommerceLiquidation` | 1422 | USD | 0.16 | 0.62 | 24.61 |
| `MarketplaceFacilitatorTax-Principal` | 22 | USD | -0.05 | -0.05 | -0.04 |
| `TaxOnRevenue` | 22 | USD | 0.04 | 0.05 | 0.05 |

## RemovalShipment / RELEASED

| breakdownType | occ. | currency | min | median | max |
|---|---:|---|---:|---:|---:|
| `AmazonFees` | 24 | USD | -0.41 | -0.41 | -0.41 |
| `RecommerceLiquidation` | 24 | USD | 0.41 | 0.41 | 0.41 |

## Retrocharge / RELEASED

| breakdownType | occ. | currency | min | median | max |
|---|---:|---|---:|---:|---:|
| `BaseTax` | 2 | USD | 9.45 | 14.91 | 20.37 |
| `MarketplaceFacilitatorTax-Principal` | 2 | USD | -20.37 | -14.91 | -9.45 |
| `ShippingTax` | 2 | USD | 0.00 | 0.00 | 0.00 |
| `Other` | 1 | USD | 20.37 | 20.37 | 20.37 |
| `RetrochargeReversal` | 1 | USD | -20.37 | -20.37 | -20.37 |

## ServiceFee / RELEASED

| breakdownType | occ. | currency | min | median | max |
|---|---:|---|---:|---:|---:|
| `FBAStorageFee` | 1707 | USD | -277.72 | -1.11 | -0.01 |
| `FBALongTermStorageFee` | 354 | USD | -194.48 | -3.64 | -0.01 |
| `FBAInboundTransportationFee` | 351 | USD | -2047.50 | -24.14 | -2.91 |
| `FBARemovalFee` | 338 | USD | -464.00 | -14.83 | -0.84 |
| `Expenses` | 202 | USD | 0.00 | 0.00 | 0.00 |
| `Sales` | 202 | USD | 0.00 | 0.00 | 0.00 |
| `FBAInboundConvenienceFee` | 123 | USD | -936.00 | -18.36 | -0.36 |
| `FBADisposalFee` | 61 | USD | -100.40 | -12.24 | -1.04 |
| `Subscription` | 6 | USD | -12.41 | -12.29 | -12.12 |
| `CouponParticipationFee` | 2 | USD | -5.00 | -5.00 | -5.00 |
| `CouponPerformanceFee` | 2 | USD | -1083.51 | -552.41 | -21.31 |
| `CustomerReturnHRRUnitFee` | 2 | USD | -15.60 | -10.40 | -5.20 |
| `PaidServicesFee` | 1 | USD | -2215.95 | -2215.95 | -2215.95 |
| `Tax` | 1 | USD | -0.23 | -0.23 | -0.23 |

## Shipment / DEFERRED

| breakdownType | occ. | currency | min | median | max |
|---|---:|---|---:|---:|---:|
| `FBAPerUnitFulfillmentFee` | 420 | USD | -18.99 | -5.61 | -4.09 |
| `OurPricePrincipal` | 420 | USD | 19.95 | 48.50 | 289.95 |
| `Commission` | 411 | USD | -43.49 | -7.28 | -2.84 |
| `OurPriceTax` | 227 | USD | 0.05 | 4.27 | 21.49 |
| `MarketplaceFacilitatorTax-Principal` | 222 | USD | -21.49 | -4.31 | -0.05 |
| `ShippingPrincipal` | 46 | USD | 0.18 | 2.99 | 44.68 |
| `ShippingDiscount` | 33 | USD | -17.09 | -2.99 | -0.27 |
| `ShippingChargeback` | 13 | USD | -44.68 | -6.32 | -0.18 |
| `OurPriceDiscount` | 5 | USD | -33.54 | -1.00 | -1.00 |
| `MarketplaceFacilitatorTax-Shipping` | 4 | USD | -0.78 | -0.58 | -0.01 |
| `ShippingTax` | 4 | USD | 0.01 | 0.58 | 0.78 |
| `MarketplaceFacilitatorVAT-Principal` | 1 | USD | -21.12 | -21.12 | -21.12 |

## Shipment / DEFERRED_RELEASED

| breakdownType | occ. | currency | min | median | max |
|---|---:|---|---:|---:|---:|
| `FBAPerUnitFulfillmentFee` | 4653 | USD | -26.08 | -5.61 | -3.95 |
| `OurPricePrincipal` | 4653 | USD | 18.95 | 48.50 | 289.95 |
| `Commission` | 4590 | USD | -56.70 | -7.28 | -2.69 |
| `OurPriceTax` | 2573 | USD | 0.02 | 3.88 | 30.44 |
| `MarketplaceFacilitatorTax-Principal` | 2542 | USD | -34.96 | -3.88 | -0.02 |
| `ShippingPrincipal` | 568 | USD | 0.07 | 2.90 | 144.36 |
| `ShippingDiscount` | 457 | USD | -37.29 | -2.06 | -0.07 |
| `ShippingChargeback` | 111 | USD | -144.36 | -4.87 | -0.10 |
| `OurPriceDiscount` | 83 | USD | -34.49 | -1.00 | -0.99 |
| `ShippingTax` | 40 | USD | 0.01 | 0.36 | 5.05 |
| `MarketplaceFacilitatorTax-Shipping` | 39 | USD | -1.95 | -0.35 | -0.01 |
| `MarketplaceFacilitatorVAT-Principal` | 2 | USD | -20.27 | -12.56 | -4.85 |
| `MarketplaceFacilitatorVAT-Shipping` | 1 | USD | -5.05 | -5.05 | -5.05 |

## Shipment / RELEASED

| breakdownType | occ. | currency | min | median | max |
|---|---:|---|---:|---:|---:|
| `FBAPerUnitFulfillmentFee` | 5672 | USD | -24.98 | -5.42 | -3.78 |
| `OurPricePrincipal` | 5672 | USD | 11.97 | 48.50 | 479.85 |
| `Commission` | 5582 | USD | -71.97 | -7.28 | -1.02 |
| `OurPriceTax` | 3317 | USD | 0.09 | 3.81 | 55.09 |
| `MarketplaceFacilitatorTax-Principal` | 3276 | USD | -39.00 | -3.88 | -0.09 |
| `ShippingPrincipal` | 614 | USD | 0.01 | 2.58 | 76.82 |
| `ShippingDiscount` | 511 | USD | -46.19 | -1.99 | -0.01 |
| `OurPriceDiscount` | 247 | USD | -40.49 | -2.99 | -0.29 |
| `ShippingChargeback` | 102 | USD | -76.82 | -5.10 | -0.07 |
| `Expenses` | 49 | USD | 0.00 | 0.00 | 0.00 |
| `Sales` | 49 | USD | 0.00 | 0.00 | 0.00 |
| `ShippingTax` | 43 | USD | 0.01 | 0.32 | 4.31 |
| `MarketplaceFacilitatorTax-Shipping` | 40 | USD | -1.04 | -0.32 | -0.01 |
| `AmazonFees` | 14 | USD | -36.40 | -7.28 | -7.28 |
| `FBAFees` | 14 | USD | -27.10 | -5.42 | -5.42 |
| `ProductCharges` | 14 | USD | 48.50 | 48.50 | 242.50 |
| `Promo` | 8 | USD | 1.80 | 14.46 | 15.59 |
| `GiftwrapChargeback` | 3 | USD | -4.49 | -4.49 | -3.99 |
| `GiftwrapPrincipal` | 3 | USD | 3.99 | 4.49 | 4.49 |
| `GiftwrapTax` | 3 | USD | 0.31 | 0.32 | 0.46 |
| `LowValueGoodsTax-Principal` | 3 | USD | -28.35 | -16.91 | -4.85 |
| `MarketplaceFacilitatorTax-Other` | 3 | USD | -0.46 | -0.32 | -0.31 |
| `MarketplaceFacilitatorVAT-Principal` | 3 | USD | -55.09 | -27.54 | -9.49 |
| `LowValueGoodsTax-Shipping` | 2 | USD | -4.31 | -4.31 | -4.31 |

## Transfer / RELEASED

| breakdownType | occ. | currency | min | median | max |
|---|---:|---|---:|---:|---:|
| `Expenses` | 22 | USD | 0.00 | 0.00 | 0.00 |
| `FundTransfer` | 22 | USD | 12.53 | 21163.88 | 56328.43 |
