"""Aggregate sp_breakdowns → pnl_monthly using BUCKET_MAP.

For each (marketplace_id, year_month, line_key) triple, sums all matching
sp_breakdown rows and writes the result to pnl_monthly.

Unmapped (transaction_type, breakdown_type) pairs are logged and written to
unmapped_breakdown_types; their monetary total also lands on line_key
"other_amz.unmapped" so nothing is silently dropped.

Usage:
    python -m sync.aggregate [--marketplace US] [--log-level INFO]
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

from .bucket_map import BUCKET_MAP, KNOWN_ZERO_TYPES
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
    # transactions that represent the monetary release of a previously-deferred order.
    # The order itself is already captured in the corresponding DEFERRED_RELEASED
    # transaction (at original shipment date). Counting both would double revenue.
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                to_char(t.posted_at AT TIME ZONE 'UTC', 'YYYY-MM') AS year_month,
                t.raw_json->>'transactionType'                       AS txn_type,
                b.breakdown_type,
                b.currency,
                SUM(b.breakdown_amount)                              AS total_amount,
                COUNT(*)                                             AS occurrences,
                MIN(t.transaction_id)                                AS sample_txn_id
            FROM sp_breakdowns b
            JOIN sp_transactions t ON t.transaction_id = b.transaction_id
            WHERE t.marketplace_id = %s
              AND t.is_deferred_release_event = false
            GROUP BY 1, 2, 3, 4
            ORDER BY 1, 2, 3
            """,
            (marketplace_id,),
        )
        rows = cur.fetchall()

    log.info(
        "Loaded %d breakdown groups for marketplace %s", len(rows), marketplace_id
    )
    stats["groups"] = len(rows)

    # ── 2. Apply BUCKET_MAP ─────────────────────────────────────────────────
    # pnl_data[(year_month, line_key)] → {line_label, bucket, amount, currency}
    pnl_data: dict[tuple[str, str], dict] = {}
    # unmapped[(txn_type, breakdown_type)] → {occurrences, sample_txn_id}
    unmapped: dict[tuple[str, str], dict] = {}
    # unmapped_by_month[(year_month)] → {amount, currency}
    unmapped_by_month: dict[str, dict] = {}

    for year_month, txn_type, breakdown_type, currency, total_amount, occurrences, sample_txn_id in rows:
        txn_type = txn_type or "Unknown"
        amount = Decimal(str(total_amount))

        if breakdown_type in KNOWN_ZERO_TYPES:
            stats["skipped_zero"] += 1
            continue

        mapping = BUCKET_MAP.get((txn_type, breakdown_type))

        if mapping is None:
            stats["unmapped_pairs"] += 1
            pair = (txn_type, breakdown_type)
            if pair not in unmapped:
                unmapped[pair] = {"occurrences": int(occurrences), "sample_txn_id": sample_txn_id}
            else:
                unmapped[pair]["occurrences"] += int(occurrences)

            ym = unmapped_by_month.setdefault(year_month, {"amount": Decimal(0), "currency": currency or "USD"})
            ym["amount"] += amount
            continue

        stats["mapped"] += 1
        line_key, line_label, bucket = mapping
        pnl_key = (year_month, line_key)
        if pnl_key not in pnl_data:
            pnl_data[pnl_key] = {
                "line_key": line_key,
                "line_label": line_label,
                "bucket": bucket,
                "amount": Decimal(0),
                "currency": currency or "USD",
            }
        pnl_data[pnl_key]["amount"] += amount

    # ── 3. Add catch-all unmapped row per month ─────────────────────────────
    for year_month, ym_data in unmapped_by_month.items():
        pnl_key = (year_month, "other_amz.unmapped")
        pnl_data[pnl_key] = {
            "line_key": "other_amz.unmapped",
            "line_label": "Unmapped breakdown types",
            "bucket": "Other AMZ transactions",
            "amount": ym_data["amount"],
            "currency": ym_data["currency"],
        }

    # ── 4. Upsert unmapped_breakdown_types ──────────────────────────────────
    if unmapped:
        log.warning(
            "%d unmapped (txn_type, breakdown_type) pairs — check bucket_map.py:",
            len(unmapped),
        )
        with conn.cursor() as cur:
            for (txn_type, breakdown_type), info in sorted(unmapped.items()):
                label = f"{txn_type}:{breakdown_type}"
                log.warning(
                    "  %-60s  %5d occurrences  sample=%s",
                    label,
                    info["occurrences"],
                    info["sample_txn_id"],
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
        log.info("All breakdown types are mapped — unmapped_breakdown_types is clean.")

    # ── 5. Write pnl_monthly ────────────────────────────────────────────────
    pnl_rows = [
        (
            marketplace_id,
            year_month,
            data["line_key"],
            data["line_label"],
            data["bucket"],
            data["amount"],
            data["currency"],
        )
        for (year_month, _line_key), data in sorted(pnl_data.items())
    ]

    with conn.cursor() as cur:
        cur.execute("DELETE FROM pnl_monthly WHERE marketplace_id = %s", (marketplace_id,))
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
        stats["groups"],
        stats["mapped"],
        stats["unmapped_pairs"],
        stats["skipped_zero"],
        stats["pnl_rows"],
    )
    return 0 if stats["unmapped_pairs"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
