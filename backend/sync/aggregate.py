"""Aggregate sp_breakdowns → pnl_monthly in Sellerise's bucket shape.

For each (marketplace_id, attribution_ym, bucket, sub_line) tuple, sums the
matching sp_breakdown rows using the (txn_type, breakdown_type, txn_status)
key that bucket_map.classify() resolves.

Attribution month per RECONCILIATION.md's PurchaseDate task:
- Shipment  → order PurchaseDate month (fallback: postedDate)
- Refund    → configurable via REFUND_BASIS (default: postedDate)
- All other → postedDate month

pnl_monthly rows land with:
- bucket    ∈ {chargesObject, feesObject, fbaObject, refundsObject, storageFee,
               expenses, passthrough}
- line_key  = Sellerise sub-line, or "{txn_type}.{breakdown_type}" for
              expenses/passthrough
- line_label= friendly label

Unmapped leaves surface as WARNING and default to expenses.

Usage:
    python -m sync.aggregate [--marketplace US] [--refund-basis posted|purchase]
                             [--log-level INFO]
"""

from __future__ import annotations

import argparse
import logging
import os
import pathlib
import sys
from collections import defaultdict
from decimal import Decimal

import psycopg
from dotenv import load_dotenv

from .attribution import (
    load_order_purchase_dates,
    order_id_from_related,
    resolve_attribution_ym,
    ym as _ym,
)
from .bucket_map import EXPENSES, BucketRule, classify
from .config import MARKETPLACE_ALIASES

log = logging.getLogger(__name__)

# Empirical decision baseline — tested against Sellerise's refundsObject.
# See reconcile.py's before/after test for the winning basis.
DEFAULT_REFUND_BASIS = "posted"


def aggregate_marketplace(
    conn: psycopg.Connection,
    marketplace_id: str,
    *,
    refund_basis: str = DEFAULT_REFUND_BASIS,
) -> dict:
    stats = {
        "transactions": 0,
        "leaves": 0,
        "mapped": 0,
        "unmapped_pairs": 0,
        "skipped_zero": 0,
        "pnl_rows": 0,
        "fallback_txns": 0,
        "fallback_by_month": {},
    }

    # ── 1. Load order → PurchaseDate map ────────────────────────────────────
    order_map = load_order_purchase_dates(conn, marketplace_id)
    log.info("Loaded %d order→PurchaseDate entries", len(order_map))

    # ── 2. Compute attribution_ym per transaction (one pass over sp_transactions) ──
    # Skip is_deferred_release_event=true — those are RELEASED release events
    # for previously-deferred orders; the original transaction is already
    # counted at its DEFERRED_RELEASED row.
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT t.transaction_id,
                   t.posted_at,
                   COALESCE(t.transaction_status, t.raw_json->>'transactionStatus') AS status,
                   t.raw_json->>'transactionType' AS txn_type,
                   t.raw_json->'relatedIdentifiers' AS related
            FROM sp_transactions t
            WHERE t.marketplace_id = %s
              AND t.is_deferred_release_event = false
            """,
            (marketplace_id,),
        )
        rows = cur.fetchall()

    txn_meta: dict[str, tuple[str, str, str]] = {}   # txn_id → (attribution_ym, txn_type, txn_status)
    fallback_txn_ids: set[str] = set()
    fallback_count_by_month: dict[str, int] = defaultdict(int)
    for txn_id, posted_at, status, txn_type, related in rows:
        oid = order_id_from_related(related or [])
        att_ym, basis = resolve_attribution_ym(
            txn_type=txn_type or "Unknown",
            posted_at=posted_at,
            order_id=oid,
            order_map=order_map,
            refund_basis=refund_basis,
        )
        if basis == "posted_fallback":
            fallback_txn_ids.add(txn_id)
            fallback_count_by_month[_ym(posted_at)] += 1
            stats["fallback_txns"] += 1
        txn_meta[txn_id] = (att_ym, txn_type or "Unknown", status or "")

    stats["transactions"] = len(txn_meta)
    fallback_amount_by_month: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    # ── 3. Iterate breakdowns, classify, aggregate keyed on attribution_ym ────
    with conn.cursor(name="agg_breakdowns") as cur:
        cur.itersize = 5000
        cur.execute(
            """
            SELECT b.transaction_id, b.breakdown_type, b.breakdown_amount, b.currency
            FROM sp_breakdowns b
            JOIN sp_transactions t ON t.transaction_id = b.transaction_id
            WHERE t.marketplace_id = %s
              AND t.is_deferred_release_event = false
            """,
            (marketplace_id,),
        )

        pnl_data: dict[tuple[str, str, str], dict] = {}
        unmapped: dict[tuple[str, str], dict] = {}

        for txn_id, breakdown_type, amount, currency in cur:
            stats["leaves"] += 1
            meta = txn_meta.get(txn_id)
            if meta is None:
                continue  # defensive; JOIN guarantees existence
            att_ym, txn_type, txn_status = meta
            amt = Decimal(str(amount))

            rule = classify(txn_type, breakdown_type, txn_status)
            if rule is None:
                stats["skipped_zero"] += 1
                continue

            if rule.bucket == EXPENSES and not _is_expected_expense(txn_type, breakdown_type):
                stats["unmapped_pairs"] += 1
                pair = (txn_type, breakdown_type)
                slot = unmapped.setdefault(pair, {"occurrences": 0, "sample_txn_id": txn_id})
                slot["occurrences"] += 1

            stats["mapped"] += 1
            key = (att_ym, rule.bucket, rule.sub_line)
            slot = pnl_data.setdefault(key, {
                "label": _label_for(rule, txn_type, breakdown_type),
                "inclusion": rule.inclusion,
                "amount": Decimal("0"),
                "currency": currency or "USD",
            })
            slot["amount"] += amt

            # Fallback $ accounting — sum absolute-value leaves for txns that
            # wanted purchase-basis but had no order-map hit.
            if txn_id in fallback_txn_ids:
                fallback_amount_by_month[att_ym] += abs(amt)

    stats["fallback_by_month"] = {
        month: {"count": fallback_count_by_month.get(month, 0),
                "amount": float(fallback_amount_by_month.get(month, Decimal("0")))}
        for month in sorted(set(fallback_count_by_month) | set(fallback_amount_by_month))
    }
    if stats["fallback_by_month"]:
        for month, agg in stats["fallback_by_month"].items():
            log.info("  fallback (posted-basis) in %s: %d txns, $%.2f leaf sum",
                     month, agg["count"], agg["amount"])

    # ── 4. Warn on unmapped leaves ─────────────────────────────────────────
    if unmapped:
        log.warning(
            "%d (txn_type, breakdown_type) pairs were not in the explicit rule "
            "table — defaulted to expenses:",
            len(unmapped),
        )
        with conn.cursor() as cur:
            for (txn_type, breakdown_type), info in sorted(unmapped.items()):
                label = f"{txn_type}:{breakdown_type}"
                log.warning("  %-60s  %5d occurrences  sample=%s",
                            label, info["occurrences"], info["sample_txn_id"])
                cur.execute(
                    """
                    INSERT INTO unmapped_breakdown_types
                        (breakdown_type, first_seen, last_seen, occurrences, sample_transaction_id)
                    VALUES (%s, now(), now(), %s, %s)
                    ON CONFLICT (breakdown_type) DO UPDATE SET
                        last_seen             = now(),
                        occurrences           = EXCLUDED.occurrences,
                        sample_transaction_id = EXCLUDED.sample_transaction_id
                    """,
                    (label, info["occurrences"], info["sample_txn_id"]),
                )
        conn.commit()
    else:
        log.info("All observed (txn_type, breakdown_type) pairs are classified.")

    # ── 5. Write pnl_monthly ───────────────────────────────────────────────
    pnl_rows = [
        (marketplace_id, att_ym, sub_line, data["label"], bucket,
         data["amount"], data["currency"])
        for (att_ym, bucket, sub_line), data in sorted(pnl_data.items())
    ]

    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM pnl_monthly WHERE marketplace_id = %s AND bucket <> 'cog'",
            (marketplace_id,),
        )
        if pnl_rows:
            cur.executemany(
                """
                INSERT INTO pnl_monthly
                    (marketplace_id, year_month, line_key, line_label, bucket, amount, currency, computed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                """,
                pnl_rows,
            )
    conn.commit()

    stats["pnl_rows"] = len(pnl_rows)
    log.info("Wrote %d pnl_monthly rows for %s (refund_basis=%s, fallback_txns=%d)",
             len(pnl_rows), marketplace_id, refund_basis, stats["fallback_txns"])
    return stats


def _label_for(rule: BucketRule, txn_type: str, breakdown_type: str) -> str:
    if rule.inclusion == "net":
        return rule.sub_line
    return f"{txn_type} · {breakdown_type}"


# ── expected expenses leaves ────────────────────────────────────────────────
_EXPECTED_EXPENSES: frozenset[tuple[str, str]] = frozenset({
    ("ServiceFee", "FBALongTermStorageFee"),
    ("ServiceFee", "FBAInboundTransportationFee"),
    ("ServiceFee", "FBAInboundConvenienceFee"),
    ("ServiceFee", "FBARemovalFee"),
    ("ServiceFee", "FBADisposalFee"),
    ("ServiceFee", "Subscription"),
    ("ServiceFee", "CouponPerformanceFee"),
    ("ServiceFee", "CouponParticipationFee"),
    ("ServiceFee", "CustomerReturnHRRUnitFee"),
    ("ServiceFee", "PaidServicesFee"),
    ("ServiceFee", "Tax"),
    ("FBAInventoryReimbursement", "FBAInventoryReimbursement"),
    ("FBAInventoryReimbursement", "FBAReversedReimbursement"),
    ("RemovalShipment", "AmazonFees"),
    ("RemovalShipment", "RecommerceLiquidation"),
    ("RemovalShipment", "TaxOnRevenue"),
    ("Adjustment", "AmazonFees"),
    ("Adjustment", "RecommerceLiquidation"),
    ("Adjustment", "Tax"),
    ("Retrocharge", "BaseTax"),
    ("Retrocharge", "ShippingTax"),
    ("Retrocharge", "Other"),
    ("Retrocharge", "RetrochargeReversal"),
    ("MiscellaneousLedgerAdjustment", "Other"),
    # UK/CA rollout — UK-specific ServiceFee leaves (EPR = Environmental
    # Producer Responsibility, InboundTransportationProgramFee). Gate 3
    # verified `expenses.other-transaction` = EPRChargebackEcoFee +
    # EPRChargebackServiceFee + Tax exactly for UK May+Jun.
    ("ServiceFee", "EPRChargebackEcoFee"),
    ("ServiceFee", "EPRChargebackServiceFee"),
    ("ServiceFee", "FBAInboundTransportationProgramFee"),
    ("ServiceFee", "DealParticipationFee"),
    ("ServiceFee", "DealPerformanceFee"),
    # AU / UK ServiceFee small extras seen
    ("ServiceFee", "Promo"),   # AU small Mar +$5.25
})


def _is_expected_expense(txn_type: str, breakdown_type: str) -> bool:
    return (txn_type, breakdown_type) in _EXPECTED_EXPENSES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync.aggregate")
    parser.add_argument("--marketplace", default="US")
    parser.add_argument("--refund-basis", default=DEFAULT_REFUND_BASIS,
                        choices=("posted", "purchase"),
                        help="Attribution basis for Refund transactions")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    load_dotenv(pathlib.Path(__file__).resolve().parents[2] / ".env")
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set", file=sys.stderr)
        return 1

    marketplace_id = MARKETPLACE_ALIASES.get(args.marketplace.upper(), args.marketplace)

    with psycopg.connect(db_url) as conn:
        stats = aggregate_marketplace(conn, marketplace_id, refund_basis=args.refund_basis)

    log.info(
        "Done: %d txns, %d leaves → %d mapped, %d unmapped pairs, %d skipped-zero, "
        "%d pnl rows, %d fallback txns",
        stats["transactions"], stats["leaves"], stats["mapped"],
        stats["unmapped_pairs"], stats["skipped_zero"], stats["pnl_rows"],
        stats["fallback_txns"],
    )
    return 0 if stats["unmapped_pairs"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
