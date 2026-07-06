"""SP-API Finances listTransactions sync (v2024-06-19).

- 180-day windowed backfill from BACKFILL_START_ISO to now() - 48h.
- Cursored resume via sync_state.
- Idempotent upsert on transaction_id.
- Flattens the nested breakdowns tree to LEAVES for sp_breakdowns.
- Extracts ProductContext (sku, asin, quantityShipped) from item.contexts.

Reference schema (fetched from developer-docs.amazon.com/sp-api/docs/finances-api-v2024-06-19-reference):

  GET /finances/2024-06-19/transactions
  Response: { payload: { nextToken, transactions: [...] } }
  Transaction:
    transactionId   (unique)
    postedDate      (ISO 8601)
    totalAmount     { currencyCode, currencyAmount }
    marketplaceDetails { marketplaceId, marketplaceName }
    breakdowns[]    { breakdownType, breakdownAmount:{currencyCode,currencyAmount}, breakdowns[] }
    items[]         { totalAmount, breakdowns[], contexts[] }
    contexts[]      polymorphic; ProductContext has { sku, asin, quantityShipped }
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterable, Iterator

import psycopg

from .sp_client import SPClient

log = logging.getLogger(__name__)

FINANCES_PATH = "/finances/2024-06-19/transactions"

# Amazon docs: postedAfter/postedBefore span must be ≤ 180 days.
# We use 179 to stay safely under the boundary.
WINDOW_DAYS = 179

# Don't sync into the last 48 hours (data may be incomplete per Amazon).
LAG_HOURS = 48


@dataclass
class SyncStats:
    windows: int = 0
    pages: int = 0
    transactions: int = 0
    breakdowns: int = 0
    items: int = 0


# ---------------- window iteration ----------------

def _iso(dt: datetime) -> str:
    """Amazon expects ISO 8601 with an explicit UTC indicator."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str) -> datetime:
    # Handles trailing 'Z' and '+00:00'.
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def _iter_windows(start: datetime, end: datetime) -> Iterator[tuple[datetime, datetime]]:
    cur = start
    while cur < end:
        w_end = min(cur + timedelta(days=WINDOW_DAYS), end)
        yield cur, w_end
        cur = w_end


# ---------------- response walking ----------------

def _flatten_breakdowns(breakdowns: list[dict[str, Any]] | None) -> Iterable[tuple[str, Decimal, str | None]]:
    """Yield (breakdown_type, amount, currency) for LEAF breakdowns only.

    A parent breakdown's amount equals the sum of its children, so flattening to
    leaves avoids double-counting during aggregation.
    """
    for b in breakdowns or []:
        children = b.get("breakdowns") or []
        if children:
            yield from _flatten_breakdowns(children)
            continue
        amt = b.get("breakdownAmount") or {}
        raw = amt.get("currencyAmount")
        if raw is None:
            continue
        yield (b["breakdownType"], Decimal(str(raw)), amt.get("currencyCode"))


def _extract_product_contexts(items: list[dict[str, Any]] | None) -> Iterable[tuple[str | None, str | None, int | None]]:
    """Yield (sku, asin, quantity_shipped) for each ProductContext under any item.

    Contexts are polymorphic. We tag a context as ProductContext by explicit
    contextType marker OR presence of sku/asin/quantityShipped fields.
    """
    for item in items or []:
        for ctx in item.get("contexts") or []:
            ctx_type = ctx.get("contextType") or ctx.get("type")
            if ctx_type and "Product" not in ctx_type:
                # Skip PaymentsContext, TimeRangeContext, etc.
                if not any(k in ctx for k in ("sku", "asin", "quantityShipped")):
                    continue
            if not any(k in ctx for k in ("sku", "asin", "quantityShipped")):
                continue
            qty = ctx.get("quantityShipped")
            yield (ctx.get("sku"), ctx.get("asin"), int(qty) if qty is not None else None)


# ---------------- sync_state helpers ----------------

def _load_state(conn: psycopg.Connection, key: str) -> tuple[datetime | None, str | None]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT last_posted_at, next_token FROM sync_state WHERE key = %s",
            (key,),
        )
        row = cur.fetchone()
    if not row:
        return None, None
    return row[0], row[1]


def _save_state(conn: psycopg.Connection, key: str, *, last_posted_at: datetime | None, next_token: str | None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO sync_state (key, last_posted_at, next_token, updated_at)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (key) DO UPDATE SET
                last_posted_at = EXCLUDED.last_posted_at,
                next_token     = EXCLUDED.next_token,
                updated_at     = now()
            """,
            (key, last_posted_at, next_token),
        )
    conn.commit()


# ---------------- transaction upsert ----------------

def _process_page(
    conn: psycopg.Connection,
    transactions: list[dict[str, Any]],
    marketplace_id: str,
    stats: SyncStats,
) -> None:
    """Batch-upsert all transactions from one API page in 5 queries total.

    Per-transaction cursor loops took ~7.5 min/page over a remote DB (one round-trip
    per transaction × ~100 ms latency). Batching reduces that to 5 round-trips
    regardless of page size, keeping us safely under the nextToken TTL.
    """
    if not transactions:
        return

    txn_rows: list[tuple] = []
    txn_ids: list[str] = []
    breakdown_rows: list[tuple] = []
    item_rows: list[tuple] = []

    for txn in transactions:
        txn_id = txn["transactionId"]
        posted_at = _parse_iso(txn["postedDate"])
        total = txn.get("totalAmount") or {}
        total_amt = Decimal(str(total["currencyAmount"])) if total.get("currencyAmount") is not None else None
        currency = total.get("currencyCode")
        md = txn.get("marketplaceDetails") or {}
        txn_marketplace = md.get("marketplaceId") or marketplace_id

        txn_rows.append((txn_id, txn_marketplace, posted_at, total_amt, currency, json.dumps(txn)))
        txn_ids.append(txn_id)

        leaves: list[tuple[str, Decimal, str | None]] = []
        leaves.extend(_flatten_breakdowns(txn.get("breakdowns")))
        for item in txn.get("items") or []:
            leaves.extend(_flatten_breakdowns(item.get("breakdowns")))
        for bt, amt, cc in leaves:
            breakdown_rows.append((txn_id, bt, amt, cc))

        for sku, asin, qty in _extract_product_contexts(txn.get("items")):
            item_rows.append((txn_id, sku, asin, qty))

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO sp_transactions (transaction_id, marketplace_id, posted_at, total_amount, currency, raw_json)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (transaction_id) DO UPDATE SET
                marketplace_id = EXCLUDED.marketplace_id,
                posted_at      = EXCLUDED.posted_at,
                total_amount   = EXCLUDED.total_amount,
                currency       = EXCLUDED.currency,
                raw_json       = EXCLUDED.raw_json,
                ingested_at    = now()
            """,
            txn_rows,
        )
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

    stats.transactions += len(txn_rows)
    stats.breakdowns += len(breakdown_rows)
    stats.items += len(item_rows)


# ---------------- main entrypoint ----------------

def sync_marketplace(
    conn: psycopg.Connection,
    client: SPClient,
    marketplace_id: str,
    *,
    start: datetime,
    end: datetime | None = None,
    debug_first_page: bool = False,
) -> SyncStats:
    """Backfill listTransactions for one marketplace into Postgres.

    Windows the range into ≤179-day slices. Persists next_token per page so a
    crashed run resumes without duplicating work.
    """
    stats = SyncStats()
    end = end or (datetime.now(timezone.utc) - timedelta(hours=LAG_HOURS))
    if start >= end:
        log.info("sync_marketplace: nothing to do (start >= end)")
        return stats

    state_key = f"sp_finances:{marketplace_id}"
    last_saved, saved_next_token = _load_state(conn, state_key)

    resume_start = last_saved if (last_saved and last_saved > start) else start

    log.info(
        "Finances sync %s: range=[%s → %s], resume_from=%s",
        marketplace_id,
        _iso(resume_start),
        _iso(end),
        _iso(resume_start) if resume_start else None,
    )

    for w_start, w_end in _iter_windows(resume_start, end):
        stats.windows += 1
        log.info("Window %d: %s → %s", stats.windows, _iso(w_start), _iso(w_end))
        next_token: str | None = saved_next_token if stats.windows == 1 else None
        # Only honor the saved next_token on the first window of a resumed run.
        saved_next_token = None
        first_call = True
        while first_call or next_token:
            first_call = False
            if next_token:
                params = {"nextToken": next_token}
            else:
                params = {
                    "postedAfter": _iso(w_start),
                    "postedBefore": _iso(w_end),
                    "marketplaceId": marketplace_id,
                }
            resp = client.get(FINANCES_PATH, params=params)
            stats.pages += 1

            if debug_first_page and stats.pages == 1:
                log.info("First-page raw response keys: %s", list(resp.keys()))
                payload_preview = resp.get("payload", {})
                log.info("Payload keys: %s", list(payload_preview.keys()))
                sample = (payload_preview.get("transactions") or [None])[0]
                if sample is not None:
                    log.info("Sample transaction keys: %s", list(sample.keys()))

            payload = resp.get("payload") or resp  # some SP-API endpoints omit the envelope
            transactions = payload.get("transactions") or []
            _process_page(conn, transactions, marketplace_id, stats)
            conn.commit()

            next_token = payload.get("nextToken")
            # If the token is still live (more pages in this window), record w_start so
            # that an expired-token restart re-fetches the whole window (safe: idempotent
            # upserts). Once the window is fully drained, advance to w_end.
            _save_state(conn, state_key,
                        last_posted_at=w_start if next_token else w_end,
                        next_token=next_token)

            log.info(
                "  page %d: %d txns (running total: %d); next_token=%s",
                stats.pages,
                len(transactions),
                stats.transactions,
                "yes" if next_token else "no",
            )

    # Backfill completed cleanly — clear next_token, leave last_posted_at at end.
    _save_state(conn, state_key, last_posted_at=end, next_token=None)
    return stats
