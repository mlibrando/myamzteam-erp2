"""Pull daily FX rates, average per month, store as native→USD in `fx_monthly_rates`.

Option A of the dashboard currency work: the dashboard shows CA/UK/AU in USD at ONE rate per
month — the average of a daily feed's rates for that month. Applying a monthly average to the
monthly P&L totals matches our data granularity (pnl_monthly is monthly) and lands within a
fraction of a percent of true per-day conversion, without a pipeline rewrite.

Source: Frankfurter (ECB daily reference rates), which tracks Google's rate closely. The feed
returns USD→native (1 USD = x native); we invert to native→USD (1 native = 1/x USD) and average
the daily inverted rates per month.

This is an offline/cron step — the API reads the stored table, never the network per request.

Usage:
    python -m sync.fx_rates                       # default: 2026-01-01 .. 2026-06-30
    python -m sync.fx_rates --start 2026-01-01 --end 2026-07-31
"""

from __future__ import annotations

import argparse
import logging
import os
import pathlib
import sys
from collections import defaultdict
from decimal import Decimal

import httpx
import psycopg
from dotenv import load_dotenv

log = logging.getLogger(__name__)

BASE_URL = "https://api.frankfurter.dev/v1"
SYMBOLS = ("CAD", "GBP", "AUD")          # non-USD marketplace currencies
SOURCE = "frankfurter(ECB), monthly avg of daily native->USD"
DEFAULT_START = "2026-01-01"
DEFAULT_END = "2026-06-30"
_RATE_Q = Decimal("0.00000001")           # 8 dp


def fetch_daily(start: str, end: str) -> dict[str, dict[str, float]]:
    """{ 'YYYY-MM-DD': {CCY: usd_to_native, ...} } from the feed's timeseries."""
    url = f"{BASE_URL}/{start}..{end}"
    resp = httpx.get(url, params={"base": "USD", "symbols": ",".join(SYMBOLS)},
                     follow_redirects=True, timeout=30.0)
    resp.raise_for_status()
    return resp.json().get("rates", {})


def monthly_averages(daily: dict[str, dict[str, float]]) -> dict[tuple[str, str], tuple[Decimal, int]]:
    """(currency, 'YYYY-MM') -> (avg native->USD, day_count). Averages daily 1/usd_to_native."""
    acc: dict[tuple[str, str], list[Decimal]] = defaultdict(list)
    for day, rates in daily.items():
        ym = day[:7]
        for ccy, usd_to_native in rates.items():
            if usd_to_native:  # guard against a zero/missing quote
                native_to_usd = Decimal("1") / Decimal(str(usd_to_native))
                acc[(ccy, ym)].append(native_to_usd)
    out: dict[tuple[str, str], tuple[Decimal, int]] = {}
    for key, vals in acc.items():
        avg = (sum(vals, Decimal("0")) / Decimal(len(vals))).quantize(_RATE_Q)
        out[key] = (avg, len(vals))
    return out


def store(conn: psycopg.Connection, averages: dict[tuple[str, str], tuple[Decimal, int]],
          source: str = SOURCE) -> int:
    with conn.cursor() as cur:
        for (ccy, ym), (rate, n) in sorted(averages.items()):
            cur.execute(
                """
                INSERT INTO fx_monthly_rates (currency, year_month, rate_to_usd, source, day_count, pulled_at)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (currency, year_month) DO UPDATE SET
                    rate_to_usd = EXCLUDED.rate_to_usd,
                    source      = EXCLUDED.source,
                    day_count   = EXCLUDED.day_count,
                    pulled_at   = now()
                """,
                (ccy, ym, rate, source, n),
            )
    conn.commit()
    return len(averages)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync.fx_rates")
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv(pathlib.Path(__file__).resolve().parents[2] / ".env")
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set", file=sys.stderr)
        return 1

    log.info("Fetching daily FX %s..%s for %s", args.start, args.end, ",".join(SYMBOLS))
    daily = fetch_daily(args.start, args.end)
    averages = monthly_averages(daily)
    if not averages:
        log.error("No rates returned for the range — nothing stored.")
        return 1
    with psycopg.connect(db_url) as conn:
        n = store(conn, averages)
    for (ccy, ym), (rate, days) in sorted(averages.items()):
        log.info("  %s %s: %s USD (avg of %d days)", ccy, ym, rate, days)
    log.info("Stored %d (currency, month) rate rows.", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
