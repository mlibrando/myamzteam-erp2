"""Rebuild sp_breakdowns and sp_transaction_items from raw_json without re-calling the API.

Run after changing the breakdown flattening logic to apply the new rules to all
already-ingested transactions.

Usage:
    python -m sync.reprocess [--marketplace US]
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

from .finances import breakdown_leaves_for_txn, _extract_product_contexts

log = logging.getLogger(__name__)

BATCH = 500  # transactions per commit


def reprocess_marketplace(conn: psycopg.Connection, marketplace_id: str) -> dict:
    stats = {"transactions": 0, "breakdowns": 0, "items": 0, "batches": 0}

    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM sp_transactions WHERE marketplace_id = %s",
            (marketplace_id,),
        )
        total = cur.fetchone()[0]
    log.info("Reprocessing %d transactions for %s", total, marketplace_id)

    offset = 0
    while True:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT transaction_id, raw_json FROM sp_transactions WHERE marketplace_id = %s ORDER BY posted_at LIMIT %s OFFSET %s",
                (marketplace_id, BATCH, offset),
            )
            rows = cur.fetchall()

        if not rows:
            break

        txn_ids = [r[0] for r in rows]
        breakdown_rows: list[tuple] = []
        item_rows: list[tuple] = []

        for txn_id, txn in rows:
            for bt, amt, cc in breakdown_leaves_for_txn(txn):
                breakdown_rows.append((txn_id, bt, amt, cc))

            for sku, asin, qty in _extract_product_contexts(txn.get("items")):
                item_rows.append((txn_id, sku, asin, qty))

        with conn.cursor() as cur:
            cur.execute("DELETE FROM sp_breakdowns WHERE transaction_id = ANY(%s)", (txn_ids,))
            cur.execute("DELETE FROM sp_transaction_items WHERE transaction_id = ANY(%s)", (txn_ids,))
            if breakdown_rows:
                cur.executemany(
                    "INSERT INTO sp_breakdowns (transaction_id, breakdown_type, breakdown_amount, currency) VALUES (%s, %s, %s, %s)",
                    breakdown_rows,
                )
            if item_rows:
                cur.executemany(
                    "INSERT INTO sp_transaction_items (transaction_id, sku, asin, quantity_shipped) VALUES (%s, %s, %s, %s)",
                    item_rows,
                )
        conn.commit()

        stats["transactions"] += len(rows)
        stats["breakdowns"] += len(breakdown_rows)
        stats["items"] += len(item_rows)
        stats["batches"] += 1
        log.info("  batch %d: %d/%d txns, %d breakdowns this batch", stats["batches"], stats["transactions"], total, len(breakdown_rows))

        offset += BATCH

    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync.reprocess")
    parser.add_argument("--marketplace", default="US")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    load_dotenv(pathlib.Path(__file__).resolve().parents[2] / ".env")
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set", file=sys.stderr)
        return 1

    from .config import MARKETPLACE_ALIASES
    marketplace_id = MARKETPLACE_ALIASES.get(args.marketplace.upper(), args.marketplace)

    with psycopg.connect(db_url) as conn:
        stats = reprocess_marketplace(conn, marketplace_id)

    log.info("Done: %d transactions, %d breakdowns, %d items in %d batches",
             stats["transactions"], stats["breakdowns"], stats["items"], stats["batches"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
