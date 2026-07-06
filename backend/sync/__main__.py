"""CLI entrypoint: `python -m sync [--marketplace US] [--debug-first-page]`.

Full pipeline (Phases 1-3):
  1. SP-API Finances backfill  → sp_transactions / sp_breakdowns / sp_transaction_items
  2. P&L aggregation           → pnl_monthly (via BUCKET_MAP)
  3. COGS import + computation → cogs_per_sku / pnl_monthly Cost-of-Goods rows

Usage:
    python -m sync [--marketplace US] [--start 2026-01-01T00:00:00Z] [--log-level INFO]
"""

from __future__ import annotations

import argparse
import logging
import os
import pathlib
import sys

import psycopg
from dotenv import load_dotenv

from .aggregate import aggregate_marketplace
from .cogs import DuplicateSkuError, compute_monthly_cogs, import_cogs
from .config import BACKFILL_START_ISO, MARKETPLACE_ALIASES, MARKETPLACE_TO_SHEET, US_MARKETPLACE_ID
from .finances import _parse_iso, make_finances_client, sync_marketplace

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync")
    parser.add_argument("--marketplace", default="US", help="Alias (US/CA/UK/AU) or literal marketplaceId")
    parser.add_argument("--start", default=BACKFILL_START_ISO, help="ISO 8601 start (default: 2026-01-01T00:00:00Z)")
    parser.add_argument("--debug-first-page", action="store_true", help="Log the shape of the first response")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    load_dotenv(pathlib.Path(__file__).resolve().parents[2] / ".env")
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 1

    marketplace_id = MARKETPLACE_ALIASES.get(args.marketplace.upper(), args.marketplace)
    start = _parse_iso(args.start)

    log.info("Starting sync for marketplace=%s from %s", marketplace_id, start)

    # ── Phase 1: SP-API Finances ─────────────────────────────────────────────
    with psycopg.connect(db_url) as conn, make_finances_client(marketplace_id) as client:
        fin_stats = sync_marketplace(
            conn, client, marketplace_id, start=start,
            debug_first_page=args.debug_first_page,
        )

    log.info(
        "Finances done: %d transactions, %d breakdowns, %d items, over %d windows / %d pages",
        fin_stats.transactions, fin_stats.breakdowns, fin_stats.items,
        fin_stats.windows, fin_stats.pages,
    )

    # ── Phase 2: P&L aggregation ─────────────────────────────────────────────
    with psycopg.connect(db_url) as conn:
        agg_stats = aggregate_marketplace(conn, marketplace_id)

    log.info(
        "Aggregate done: %d groups → %d mapped, %d unmapped pairs, %d pnl rows",
        agg_stats["groups"], agg_stats["mapped"],
        agg_stats["unmapped_pairs"], agg_stats["pnl_rows"],
    )

    # ── Phase 3: COGS ────────────────────────────────────────────────────────
    sheet_name = MARKETPLACE_TO_SHEET.get(marketplace_id)
    if sheet_name:
        with psycopg.connect(db_url) as conn:
            try:
                cogs_imported = import_cogs(conn, marketplace_id, sheet_name)
            except DuplicateSkuError as exc:
                log.error("COGS import aborted: %s", exc)
                return 1

            cogs_stats = compute_monthly_cogs(conn, marketplace_id)

        log.info(
            "COGS done: %d SKUs imported, %d months, %d missing SKUs",
            cogs_imported, cogs_stats["months"], cogs_stats["missing_skus"],
        )
    else:
        log.warning("No COGS sheet mapping for marketplace %s — skipping COGS", marketplace_id)

    rc = 0
    if agg_stats["unmapped_pairs"]:
        rc = 2
    elif sheet_name and cogs_stats["missing_skus"]:
        rc = 2
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
