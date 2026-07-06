"""Aggregate sp_breakdowns → pnl_monthly in Sellerise's bucket shape.

For each (marketplace_id, year_month, bucket, sub_line) tuple, sums the matching
sp_breakdown rows using the (txn_type, breakdown_type, txn_status) key that
bucket_map.classify() resolves.

pnl_monthly rows land with:
- bucket    ∈ {chargesObject, feesObject, fbaObject, refundsObject, storageFee,
               expenses, passthrough}
- line_key  = Sellerise sub-line ("Principal", "Commission", ...) or, for
              expenses/passthrough, "{txn_type}.{breakdown_type}" for auditing
- line_label= friendly label (equal to sub_line for net; equal to
              "{txn_type} · {breakdown_type}" for expenses/passthrough)

Unmapped leaves (no rule at all in bucket_map — should never happen since the
probe verified 0 unmapped) surface as WARNING and default to expenses so they
stay out of net.

Usage:
    python -m sync.aggregate [--marketplace US] [--log-level INFO]
"""

from __future__ import annotations

import argparse
import logging
import os
import pathlib
import sys
from decimal import Decimal

import psycopg
from dotenv import load_dotenv

from .bucket_map import EXPENSES, BucketRule, classify
from .config import MARKETPLACE_ALIASES

log = logging.getLogger(__name__)


def aggregate_marketplace(conn: psycopg.Connection, marketplace_id: str) -> dict:
    stats = {
        "groups": 0,
        "mapped": 0,
        "unmapped_pairs": 0,
        "skipped_zero": 0,
        "pnl_rows": 0,
    }

    # ── 1. Load grouped breakdown sums ──────────────────────────────────────
    # Exclude is_deferred_release_event = true rows: these are RELEASED Shipment
    # transactions that represent the monetary release of a previously-deferred
    # order. The order itself is already captured in the corresponding
    # DEFERRED_RELEASED transaction (at original shipment date). Counting both
    # would double revenue.
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                to_char(t.posted_at AT TIME ZONE 'UTC', 'YYYY-MM') AS year_month,
                t.raw_json->>'transactionType'                     AS txn_type,
                COALESCE(t.transaction_status,
                         t.raw_json->>'transactionStatus')         AS txn_status,
                b.breakdown_type,
                b.currency,
                SUM(b.breakdown_amount)                            AS total_amount,
                COUNT(*)                                           AS occurrences,
                MIN(t.transaction_id)                              AS sample_txn_id
            FROM sp_breakdowns b
            JOIN sp_transactions t ON t.transaction_id = b.transaction_id
            WHERE t.marketplace_id = %s
              AND t.is_deferred_release_event = false
            GROUP BY 1, 2, 3, 4, 5
            ORDER BY 1, 2, 3, 4
            """,
            (marketplace_id,),
        )
        rows = cur.fetchall()

    log.info("Loaded %d breakdown groups for marketplace %s", len(rows), marketplace_id)
    stats["groups"] = len(rows)

    # ── 2. Apply BUCKET_MAP.classify() ─────────────────────────────────────
    # pnl_data[(ym, bucket, sub_line)] → {label, amount, currency}
    pnl_data: dict[tuple[str, str, str], dict] = {}
    # unmapped[(txn_type, breakdown_type)] → {occurrences, sample_txn_id}
    unmapped: dict[tuple[str, str], dict] = {}

    for ym, txn_type, txn_status, breakdown_type, currency, total_amount, occurrences, sample_txn_id in rows:
        txn_type = txn_type or "Unknown"
        amount = Decimal(str(total_amount))

        rule = classify(txn_type, breakdown_type, txn_status)
        if rule is None:
            # KNOWN_ZERO_TYPES — wrapper nodes, always zero.
            stats["skipped_zero"] += 1
            continue

        # classify() always returns *something* for unknown leaves (default =
        # expenses). But the probe already covers every leaf we've seen, so if
        # a leaf falls into expenses via the catch-all, that's fine —
        # `unmapped` is reserved for future new leaves the probe didn't cover.
        # We flag "genuinely new" leaves here by checking whether they matched
        # any explicit rule. Since classify() folds new + known-expenses into
        # the same expenses bucket, we can't distinguish without a second
        # pass — see _is_expected_expense() below.
        if rule.bucket == EXPENSES and not _is_expected_expense(txn_type, breakdown_type):
            stats["unmapped_pairs"] += 1
            pair = (txn_type, breakdown_type)
            slot = unmapped.setdefault(
                pair, {"occurrences": 0, "sample_txn_id": sample_txn_id}
            )
            slot["occurrences"] += int(occurrences)

        stats["mapped"] += 1
        key = (ym, rule.bucket, rule.sub_line)
        slot = pnl_data.setdefault(key, {
            "label": _label_for(rule, txn_type, breakdown_type),
            "inclusion": rule.inclusion,
            "amount": Decimal("0"),
            "currency": currency or "USD",
        })
        slot["amount"] += amount

    # ── 3. Warn on unmapped leaves ─────────────────────────────────────────
    if unmapped:
        log.warning(
            "%d (txn_type, breakdown_type) pairs were not in the explicit rule "
            "table — defaulted to expenses. Add rules or add to _EXPECTED_EXPENSES:",
            len(unmapped),
        )
        with conn.cursor() as cur:
            for (txn_type, breakdown_type), info in sorted(unmapped.items()):
                label = f"{txn_type}:{breakdown_type}"
                log.warning(
                    "  %-60s  %5d occurrences  sample=%s",
                    label, info["occurrences"], info["sample_txn_id"],
                )
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

    # ── 4. Write pnl_monthly ───────────────────────────────────────────────
    pnl_rows = [
        (marketplace_id, ym, sub_line, data["label"], bucket,
         data["amount"], data["currency"])
        for (ym, bucket, sub_line), data in sorted(pnl_data.items())
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
    log.info("Wrote %d pnl_monthly rows for %s", len(pnl_rows), marketplace_id)
    return stats


def _label_for(rule: BucketRule, txn_type: str, breakdown_type: str) -> str:
    """Human-readable label for a pnl_monthly row."""
    if rule.inclusion == "net":
        return rule.sub_line
    return f"{txn_type} · {breakdown_type}"


# ── expected expenses leaves ────────────────────────────────────────────────
# Every (txn_type, breakdown_type) that legitimately lands in the expenses
# bucket via the classify() catch-all. These are known real leaves; anything
# outside this set that ends up in expenses is a NEW leaf and gets a WARNING.
# Sourced from reference/data/probe_breakdowns.md.

_EXPECTED_EXPENSES: frozenset[tuple[str, str]] = frozenset({
    # ServiceFee — real seller costs
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
    # FBA reimbursements
    ("FBAInventoryReimbursement", "FBAInventoryReimbursement"),
    ("FBAInventoryReimbursement", "FBAReversedReimbursement"),
    # RemovalShipment / liquidations
    ("RemovalShipment", "AmazonFees"),
    ("RemovalShipment", "RecommerceLiquidation"),
    ("RemovalShipment", "TaxOnRevenue"),
    # Adjustments and misc
    ("Adjustment", "AmazonFees"),
    ("Adjustment", "RecommerceLiquidation"),
    ("Adjustment", "Tax"),
    ("Adjustment", "ReserveCredit"),
    ("Adjustment", "ReserveDebit"),
    ("Retrocharge", "BaseTax"),
    ("Retrocharge", "ShippingTax"),
    ("Retrocharge", "Other"),
    ("Retrocharge", "RetrochargeReversal"),
    ("MiscellaneousLedgerAdjustment", "Other"),
    ("Transfer", "FundTransfer"),
})


def _is_expected_expense(txn_type: str, breakdown_type: str) -> bool:
    return (txn_type, breakdown_type) in _EXPECTED_EXPENSES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync.aggregate")
    parser.add_argument("--marketplace", default="US")
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
        stats = aggregate_marketplace(conn, marketplace_id)

    log.info(
        "Done: %d groups → %d mapped, %d unmapped pairs, %d skipped-zero, %d pnl rows",
        stats["groups"], stats["mapped"], stats["unmapped_pairs"],
        stats["skipped_zero"], stats["pnl_rows"],
    )
    return 0 if stats["unmapped_pairs"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
