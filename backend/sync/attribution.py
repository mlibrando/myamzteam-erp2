"""Attribution-date resolution for pnl aggregation.

Sellerise attributes revenue by order PurchaseDate; SP-API `listTransactions`
returns `postedDate`. This module resolves the *attribution month* for each
transaction, using the `order_purchase_date` map for order-linked transactions
and falling back to `postedDate` otherwise.

Policy per RECONCILIATION.md task 2 (order PurchaseDate re-attribution):
- Shipment           → PurchaseDate month (via ORDER_ID → order_purchase_date)
- Refund             → configurable; empirical basis test picks between
                       'purchase' and 'posted'. Default: 'posted'.
- Everything else    → postedDate month (no order id, or order not in map)

Anything missing from the map falls back to postedDate; the aggregator logs
counts + $ of fallbacks per month.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Iterable

import psycopg

log = logging.getLogger(__name__)


def load_order_purchase_dates(conn: psycopg.Connection, marketplace_id: str,
                              ingested_before: datetime | None = None) -> dict[str, datetime]:
    """Return {order_id: purchase_date_utc} for one marketplace.

    `ingested_before` restricts the map to orders ingested at or before that
    instant. Used only by the drift guard, to reconstruct a cell as it stood at a
    pinned defect's `measured_at` horizon. Leave it None for normal operation.
    """
    sql = "SELECT order_id, purchase_date FROM order_purchase_date WHERE marketplace_id = %s"
    params: tuple = (marketplace_id,)
    if ingested_before is not None:
        sql += " AND ingested_at <= %s"
        params += (ingested_before,)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return {r[0]: r[1] for r in cur.fetchall()}


def order_id_from_related(related_identifiers: Iterable[dict[str, Any]] | None) -> str | None:
    """Extract AmazonOrderId from a transaction's relatedIdentifiers list."""
    for ri in related_identifiers or []:
        if ri.get("relatedIdentifierName") == "ORDER_ID":
            return ri.get("relatedIdentifierValue")
    return None


def ym(dt: datetime) -> str:
    """UTC year-month string 'YYYY-MM'."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m")


def resolve_attribution_ym(
    *,
    txn_type: str,
    posted_at: datetime,
    order_id: str | None,
    order_map: dict[str, datetime],
    refund_basis: str = "posted",
) -> tuple[str, str]:
    """Return (attribution_ym, basis_used) for one transaction.

    basis_used ∈ {"purchase", "posted", "posted_fallback"}:
      - "purchase"       — used PurchaseDate from the order map
      - "posted"         — used postedDate by design (non-order txn, or refund
                           with refund_basis='posted')
      - "posted_fallback" — wanted purchase-date but the order id was missing
                            from the map (log for buffer-window diagnostics)
    """
    # Non-order transactions: always postedDate.
    if txn_type not in ("Shipment", "Refund"):
        return ym(posted_at), "posted"

    # Refund basis is empirical — the caller sets it.
    if txn_type == "Refund" and refund_basis == "posted":
        return ym(posted_at), "posted"

    # Shipment or Refund on purchase basis.
    if not order_id:
        return ym(posted_at), "posted_fallback"
    pd = order_map.get(order_id)
    if pd is None:
        return ym(posted_at), "posted_fallback"
    return ym(pd), "purchase"


__all__ = [
    "load_order_purchase_dates",
    "order_id_from_related",
    "resolve_attribution_ym",
    "ym",
]
