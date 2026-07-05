"""CLI entrypoint: `python -m sync [--marketplace US] [--debug-first-page]`.

Loads .env from the repo root, opens Postgres, and runs the US Finances backfill.
Phase 1 scope: SP-API Finances only. Later phases add ads / sales / aggregation.
"""

from __future__ import annotations

import argparse
import logging
import os
import pathlib
import sys

import psycopg
from dotenv import load_dotenv

from .config import BACKFILL_START_ISO, US_MARKETPLACE_ID
from .finances import _parse_iso, sync_marketplace
from .sp_client import SPClient


MARKETPLACE_ALIASES = {
    "US": "ATVPDKIKX0DER",
    "CA": "A2EUQ1WTGCTBG2",
    "UK": "A1F83G8C2ARO7P",
    "AU": "A39IBJ37TRP1C6",
}


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
    if marketplace_id != US_MARKETPLACE_ID:
        logging.getLogger(__name__).warning(
            "Phase 1 targets US only. Marketplace %s will be attempted but is not covered by acceptance tests yet.",
            marketplace_id,
        )

    start = _parse_iso(args.start)

    logging.getLogger(__name__).info("Starting sync for marketplace=%s from %s", marketplace_id, start)

    with psycopg.connect(db_url) as conn, SPClient.for_marketplace(marketplace_id) as client:
        stats = sync_marketplace(
            conn,
            client,
            marketplace_id,
            start=start,
            debug_first_page=args.debug_first_page,
        )

    logging.getLogger(__name__).info(
        "Done: %d transactions, %d breakdowns, %d items, over %d windows / %d pages",
        stats.transactions,
        stats.breakdowns,
        stats.items,
        stats.windows,
        stats.pages,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
