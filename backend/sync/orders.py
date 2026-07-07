"""Orders API sweep — persist AmazonOrderId → PurchaseDate for re-attribution.

Sellerise attributes revenue by order PurchaseDate. `listTransactions` returns
`postedDate` (when the financial event posted). The two differ by 0–2 days for
typical orders, but transactions posting across a month boundary land in
different months under each scheme. Persisting an AmazonOrderId → PurchaseDate
map lets `aggregate.py` re-key Shipment / Refund attribution to purchase-date
months.

Design:
- Bulk `OrdersV0.get_orders(CreatedAfter=..., CreatedBefore=..., MarketplaceIds=[...])`,
  paginated on `resp.next_token` (this endpoint returns `NextToken`, not
  `nextToken`; the library's ApiResponse handles the case difference).
- Sweep in ≤180-day windows for symmetry with the finances sync, though the
  Orders API allows longer.
- Cursored resume via `sync_state` keyed on `orders:{marketplace_id}` so a
  crashed sweep picks up mid-window.
- Idempotent upsert on AmazonOrderId — safe to re-run.
- Rate-limit-friendly: OrdersV0 is ~1 req/min sustained; sleep between calls
  keyed off `resp.rate_limit` when present, or a fixed 60s fallback.

Usage:
    python -m sync.orders [--marketplace US] [--start 2025-12-01T00:00:00Z]
"""

from __future__ import annotations

import argparse
import logging
import os
import pathlib
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator

import psycopg
from dotenv import load_dotenv
from sp_api.api import OrdersV0
from sp_api.base.exceptions import SellingApiRequestThrottledException

from .config import MARKETPLACE_ALIASES, MARKETPLACE_TO_ENUM, credentials_for
from .finances import _iso, _parse_iso

log = logging.getLogger(__name__)

# Orders API rate policy: sustained 0.0167 rps + burst 20.
# Use a token bucket so the first ~20 pages fire back-to-back, then throttle to
# ~1 page/min sustained. Refill rate = sustained rate.
_BURST_CAPACITY = 20
_REFILL_RATE_RPS = 0.0167  # per Amazon; also seen in resp.rate_limit
_MAX_THROTTLE_RETRIES = 8


@dataclass
class SweepStats:
    windows: int = 0
    pages: int = 0
    orders_seen: int = 0
    orders_written: int = 0


def make_orders_client(marketplace_id: str) -> OrdersV0:
    return OrdersV0(
        marketplace=MARKETPLACE_TO_ENUM[marketplace_id],
        credentials=credentials_for(marketplace_id),
    )


def _iter_windows(start: datetime, end: datetime, span_days: int = 30) -> Iterator[tuple[datetime, datetime]]:
    """Small windows so per-page state saves cover reasonable ground on restart."""
    cur = start
    while cur < end:
        w_end = min(cur + timedelta(days=span_days), end)
        yield cur, w_end
        cur = w_end


class _TokenBucket:
    """Amazon burst pool: capacity 20, refill 0.0167 tokens/second."""

    def __init__(self, capacity: int = _BURST_CAPACITY, refill_rps: float = _REFILL_RATE_RPS):
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.refill_rps = refill_rps
        self.last = time.monotonic()

    def acquire(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rps)
        self.last = now
        if self.tokens < 1.0:
            sleep_s = (1.0 - self.tokens) / self.refill_rps
            time.sleep(sleep_s)
            self.tokens = 0.0
            self.last = time.monotonic()
        else:
            self.tokens -= 1.0


def _call_with_throttle(client: OrdersV0, params: dict[str, Any], bucket: _TokenBucket) -> Any:
    delay = 30.0
    for attempt in range(_MAX_THROTTLE_RETRIES):
        bucket.acquire()
        try:
            return client.get_orders(**params)
        except SellingApiRequestThrottledException:
            if attempt == _MAX_THROTTLE_RETRIES - 1:
                raise
            log.warning("Throttled on get_orders; sleeping %.0fs", delay)
            time.sleep(delay)
            delay = min(300.0, delay * 1.5)
            # Empty the bucket after a 429 — burst is exhausted.
            bucket.tokens = 0.0
            bucket.last = time.monotonic()
    raise RuntimeError("unreachable")


def _load_state(conn: psycopg.Connection, key: str) -> tuple[datetime | None, str | None]:
    with conn.cursor() as cur:
        cur.execute("SELECT last_posted_at, next_token FROM sync_state WHERE key = %s", (key,))
        row = cur.fetchone()
    return (row[0], row[1]) if row else (None, None)


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


def _upsert_orders(conn: psycopg.Connection, marketplace_id: str, orders: list[dict[str, Any]]) -> int:
    """Batch upsert; returns rows written."""
    if not orders:
        return 0
    rows = []
    for o in orders:
        oid = o.get("AmazonOrderId")
        pd = o.get("PurchaseDate")
        if not oid or not pd:
            continue
        rows.append((
            oid, marketplace_id, _parse_iso(pd),
            _parse_iso(o["LastUpdateDate"]) if o.get("LastUpdateDate") else None,
            o.get("OrderStatus"),
        ))
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO order_purchase_date
                (order_id, marketplace_id, purchase_date, last_update, order_status)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (order_id) DO UPDATE SET
                marketplace_id = EXCLUDED.marketplace_id,
                purchase_date  = EXCLUDED.purchase_date,
                last_update    = EXCLUDED.last_update,
                order_status   = EXCLUDED.order_status,
                ingested_at    = now()
            """,
            rows,
        )
    conn.commit()
    return len(rows)


def sweep_orders(
    conn: psycopg.Connection,
    client: OrdersV0,
    marketplace_id: str,
    *,
    start: datetime,
    end: datetime | None = None,
) -> SweepStats:
    stats = SweepStats()
    end = end or datetime.now(timezone.utc)
    state_key = f"orders:{marketplace_id}"
    last_saved, saved_next_token = _load_state(conn, state_key)
    resume_start = last_saved if (last_saved and last_saved > start) else start

    log.info("Orders sweep %s: range=[%s → %s], resume_from=%s",
             marketplace_id, _iso(resume_start), _iso(end), _iso(resume_start))

    bucket = _TokenBucket()
    for w_start, w_end in _iter_windows(resume_start, end):
        stats.windows += 1
        log.info("Window %d: %s → %s", stats.windows, _iso(w_start), _iso(w_end))
        next_token: str | None = saved_next_token if stats.windows == 1 else None
        saved_next_token = None
        first_call = True
        while first_call or next_token:
            first_call = False
            if next_token:
                params: dict[str, Any] = {"NextToken": next_token, "MarketplaceIds": [marketplace_id]}
            else:
                params = {
                    "CreatedAfter": _iso(w_start),
                    "CreatedBefore": _iso(w_end),
                    "MarketplaceIds": [marketplace_id],
                }
            resp = _call_with_throttle(client, params, bucket)
            stats.pages += 1

            payload = resp.payload or {}
            orders = payload.get("Orders") or []
            stats.orders_seen += len(orders)
            stats.orders_written += _upsert_orders(conn, marketplace_id, orders)

            next_token = resp.next_token
            _save_state(conn, state_key,
                        last_posted_at=w_start if next_token else w_end,
                        next_token=next_token)
            log.info("  page %d: %d orders (running written: %d); next_token=%s; rate_limit=%s",
                     stats.pages, len(orders), stats.orders_written,
                     "yes" if next_token else "no", resp.rate_limit)

    _save_state(conn, state_key, last_posted_at=end, next_token=None)
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync.orders")
    parser.add_argument("--marketplace", default="US")
    parser.add_argument("--start", default="2025-12-01T00:00:00Z",
                        help="ISO 8601 CreatedAfter (default Dec buffer)")
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
    start = _parse_iso(args.start)

    log.info("Starting Orders sweep for marketplace=%s from %s", marketplace_id, start)
    with psycopg.connect(db_url) as conn, make_orders_client(marketplace_id) as client:
        stats = sweep_orders(conn, client, marketplace_id, start=start)

    log.info("Done: %d windows, %d pages, %d orders seen, %d written",
             stats.windows, stats.pages, stats.orders_seen, stats.orders_written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
