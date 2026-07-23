"""Aggregate sp_breakdowns → pnl_daily (day grain) for the dashboard's custom date range.

Same classification (bucket_map.classify), attribution, and COGS math as the monthly build
(sync.aggregate + sync.cogs) — just keyed on the FULL attribution date instead of the month.
Because the day's month equals the monthly pipeline's attribution month, Σ pnl_daily over a
month == pnl_monthly; `reconcile_against_monthly` guards that invariant (to the cent).

The monthly pipeline is untouched: this is a parallel writer to a separate table.

Usage:
    python -m sync.aggregate_daily [--marketplace US] [--log-level INFO]   # + reconcile guard
"""

from __future__ import annotations

import argparse
import logging
import os
import pathlib
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal

import psycopg
from dotenv import load_dotenv

from .attribution import (
    load_order_purchase_dates,
    order_id_from_related,
    resolve_attribution_date,
)
from .bucket_map import classify
from .config import (
    MARKETPLACE_ALIASES,
    MARKETPLACE_CURRENCY,
    MARKETPLACE_REFUND_BASIS,
    MARKETPLACE_REFUND_COGS_BASIS,
    cog_currency,
    cog_source_marketplace,
)

log = logging.getLogger(__name__)

_CENT = Decimal("0.01")


def _txn_meta(conn: psycopg.Connection, marketplace_id: str,
              order_map: dict[str, datetime], refund_basis: str) -> dict[str, tuple[date, str, str]]:
    """txn_id → (attribution_date, txn_type, txn_status). Mirrors sync.aggregate's pass."""
    meta: dict[str, tuple[date, str, str]] = {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT t.transaction_id, t.posted_at,
                   COALESCE(t.transaction_status, t.raw_json->>'transactionStatus') AS status,
                   t.raw_json->>'transactionType' AS txn_type,
                   t.raw_json->'relatedIdentifiers' AS related
            FROM sp_transactions t
            WHERE t.marketplace_id = %s AND t.is_deferred_release_event = false
            """,
            (marketplace_id,),
        )
        for tid, posted_at, status, txn_type, related in cur.fetchall():
            oid = order_id_from_related(related or [])
            att_dt, _basis = resolve_attribution_date(
                txn_type=txn_type or "Unknown", posted_at=posted_at,
                order_id=oid, order_map=order_map, refund_basis=refund_basis,
            )
            meta[tid] = (att_dt.astimezone(timezone.utc).date(), txn_type or "Unknown", status or "")
    return meta


def _daily_rows(conn: psycopg.Connection, marketplace_id: str) -> list[tuple]:
    """Build the full pnl_daily row set for one marketplace (aggregate buckets + cog)."""
    native_ccy = MARKETPLACE_CURRENCY.get(marketplace_id, "USD")
    order_map = load_order_purchase_dates(conn, marketplace_id)
    meta = _txn_meta(conn, marketplace_id, order_map,
                     MARKETPLACE_REFUND_BASIS.get(marketplace_id, "posted"))

    # ── aggregate buckets (everything except cog) ─────────────────────────────
    agg: dict[tuple[date, str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    ccy: dict[tuple[date, str, str], str] = {}
    with conn.cursor(name="agg_daily") as cur:
        cur.itersize = 5000
        cur.execute(
            """
            SELECT b.transaction_id, b.breakdown_type, b.breakdown_amount, b.currency
            FROM sp_breakdowns b JOIN sp_transactions t ON t.transaction_id = b.transaction_id
            WHERE t.marketplace_id = %s AND t.is_deferred_release_event = false
            """,
            (marketplace_id,),
        )
        for tid, breakdown_type, amount, currency in cur:
            m = meta.get(tid)
            if m is None:
                continue
            day, txn_type, txn_status = m
            rule = classify(txn_type, breakdown_type, txn_status)
            if rule is None:
                continue
            key = (day, rule.bucket, rule.sub_line)
            agg[key] += Decimal(str(amount))
            ccy.setdefault(key, currency or native_ccy)

    rows: list[tuple] = [
        (marketplace_id, day, sub_line, sub_line, bucket, amount, ccy[(day, bucket, sub_line)])
        for (day, bucket, sub_line), amount in agg.items() if amount != 0
    ]

    # ── COGS at day grain (exact sync.cogs SQL; grain = ::date; SIGNED per day) ──
    cog_mp = cog_source_marketplace(marketplace_id)
    rbasis = MARKETPLACE_REFUND_COGS_BASIS.get(marketplace_id, "purchase")
    refund_date_expr = ("COALESCE(opd.purchase_date, t.posted_at)"
                        if rbasis == "purchase" else "t.posted_at")
    with conn.cursor() as cur:
        cur.execute(
            f"""
            WITH ship_or_refund AS (
              SELECT i.sku,
                     CASE (t.raw_json->>'transactionType')
                          WHEN 'Shipment' THEN  i.quantity_shipped
                          WHEN 'Refund'   THEN -i.quantity_shipped END AS net_qty,
                     (CASE (t.raw_json->>'transactionType')
                          WHEN 'Shipment' THEN COALESCE(opd.purchase_date, t.posted_at)
                          WHEN 'Refund'   THEN {refund_date_expr}
                      END AT TIME ZONE 'UTC')::date AS d
              FROM sp_transaction_items i
              JOIN sp_transactions t ON t.transaction_id = i.transaction_id
              LEFT JOIN LATERAL (
                  SELECT ri->>'relatedIdentifierValue' AS order_id
                  FROM jsonb_array_elements(t.raw_json->'relatedIdentifiers') ri
                  WHERE ri->>'relatedIdentifierName' = 'ORDER_ID' LIMIT 1) rel ON true
              LEFT JOIN order_purchase_date opd
                ON opd.order_id = rel.order_id AND opd.marketplace_id = t.marketplace_id
              WHERE t.marketplace_id = %s AND t.is_deferred_release_event = false
                AND (t.raw_json->>'transactionType') IN ('Shipment', 'Refund')
                AND i.quantity_shipped > 0)
            SELECT sr.d, SUM(sr.net_qty * c.cogs) AS cog
            FROM ship_or_refund sr JOIN cogs_per_sku c
              ON c.sku = sr.sku AND c.marketplace_id = %s
            GROUP BY 1
            """,
            (marketplace_id, cog_mp),
        )
        cog_ccy = cog_currency(marketplace_id)
        for d, cog in cur.fetchall():
            amt = Decimal(str(cog))
            if amt != 0:
                rows.append((marketplace_id, d, "cog", "Cost of goods sold", "cog", amt, cog_ccy))
    return rows


def aggregate_daily_marketplace(conn: psycopg.Connection, marketplace_id: str) -> dict:
    """Rebuild pnl_daily for one marketplace (delete-all-for-mp + insert)."""
    rows = _daily_rows(conn, marketplace_id)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM pnl_daily WHERE marketplace_id = %s", (marketplace_id,))
        cur.executemany(
            """
            INSERT INTO pnl_daily
                (marketplace_id, date, line_key, line_label, bucket, amount, currency, computed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, now())
            """,
            rows,
        )
    conn.commit()
    log.info("Wrote %d pnl_daily rows for %s", len(rows), marketplace_id)
    return {"rows": len(rows)}


def reconcile_against_monthly(conn: psycopg.Connection, marketplace_id: str) -> list[tuple]:
    """Guard: Σ pnl_daily over each month must equal pnl_monthly (cog compared on |Σ|).

    Returns a list of (year_month, bucket, line_key, daily, monthly, delta) mismatches > 1¢.
    Empty list == the daily table reconstructs the reconciled monthly numbers exactly.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT to_char(date, 'YYYY-MM') AS ym, bucket, line_key,
                   CASE WHEN bucket = 'cog' THEN abs(SUM(amount)) ELSE SUM(amount) END
            FROM pnl_daily WHERE marketplace_id = %s
            GROUP BY 1, 2, 3
            """,
            (marketplace_id,),
        )
        daily = {(y, b, lk): Decimal(str(a)) for y, b, lk, a in cur.fetchall()}
        cur.execute(
            "SELECT year_month, bucket, line_key, amount FROM pnl_monthly WHERE marketplace_id = %s",
            (marketplace_id,),
        )
        monthly = {(y, b, lk): Decimal(str(a)) for y, b, lk, a in cur.fetchall()}

    out: list[tuple] = []
    for key in set(daily) | set(monthly):
        dv, mv = daily.get(key, Decimal("0")), monthly.get(key, Decimal("0"))
        if abs(dv - mv) > _CENT:
            out.append((key[0], key[1], key[2], float(dv), float(mv), float(dv - mv)))
    return sorted(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync.aggregate_daily")
    parser.add_argument("--marketplace", default="ALL")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv(pathlib.Path(__file__).resolve().parents[2] / ".env")
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set", file=sys.stderr)
        return 1

    if args.marketplace.upper() == "ALL":
        mps = list(MARKETPLACE_ALIASES.values())
    else:
        mps = [MARKETPLACE_ALIASES.get(args.marketplace.upper(), args.marketplace)]

    total_mismatch = 0
    with psycopg.connect(db_url) as conn:
        for mp in mps:
            aggregate_daily_marketplace(conn, mp)
            bad = reconcile_against_monthly(conn, mp)
            total_mismatch += len(bad)
            if bad:
                log.error("RECONCILE FAIL %s: %d mismatch(es) vs pnl_monthly", mp, len(bad))
                for row in bad[:20]:
                    log.error("  %s", row)
            else:
                log.info("reconcile OK %s: Σ pnl_daily/month == pnl_monthly", mp)
    return 0 if total_mismatch == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
