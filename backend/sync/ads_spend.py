"""Amazon Ads monthly-spend pull → ad_spend_daily.

Per Phase-4 Step-2 design: one report per month, `date.value` + `campaign.id` +
`adProduct.value` + `budgetCurrency.value` + `metric.totalCost`, persisted with a
per-row `as_of` timestamp.

**One NA report carries every marketplace.** Amazon returns a single report per
month for the NA advertiser account, and its rows are separated only by
`budgetCurrency.value`: USD→US, CAD→CA, GBP→UK, AUD→AU. Each row is routed to the
marketplace whose native ad currency it carries, which is exactly what the readers
select (`reconcile.py`'s `budget_currency = MARKETPLACE_AD_CURRENCY[mp]` and
`reconcile_au.py`'s `'AUD'`).

This module previously dropped every non-USD row and tagged what was left with
whatever `--marketplace` said. Against CA/UK/AU that deleted the reconciled rows
and inserted USD rows the readers could never select. Do not reintroduce a
single-currency filter here.

Restatement handling: rows include `as_of`. Re-pulling a month deletes and
re-inserts its rows with a fresh `as_of`. This makes restatement drift
(expected sub-dollar month deltas after Amazon revises) distinguishable from a
real pipeline bug — the timestamp is the audit trail.

Rate handling (empirical, Step 1 findings + this build):
- `POST /adsApi/v1/create/reports` throttles fast under bursts. Space submits
  ~60 s apart and add exponential backoff on 429. The plan calls out that the
  in-flight/RPS limit must be verified before parallelising; this module is
  serial by default. Set `--parallel-submit N` to try more at once.
- `POST /adsApi/v1/retrieve/reports` accepts ONE reportId per call (400000 on
  a list). Poll each report individually.
- Report generation is slow and scales with the month: 2026-01 (11,337 rows) took
  ~19 min, past the 20-minute default batch cap. Raise `--batch-timeout-s` for
  large months. A month that times out is never written, so its rows survive.

Usage:
    # regenerate every marketplace for a range, straight into the real table
    python -m sync.ads_spend --marketplace ALL --start 2026-01-01 --end 2026-05-31

    # verify a pull before it touches the reconciled rows
    python -m sync.ads_spend --marketplace ALL --start 2026-01-01 --end 2026-05-31 \
                             --table ad_spend_daily_scratch --batch-timeout-s 2700
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import logging
import os
import pathlib
import sys
import time
from decimal import Decimal
from typing import Any

import psycopg
from dotenv import load_dotenv

from .ads_client import AdsClient, AdsAPIError
from .ads_probe import create_probe_report, list_accounts
from .config import MARKETPLACE_AD_CURRENCY, MARKETPLACE_ALIASES, US_MARKETPLACE_ID

log = logging.getLogger(__name__)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

_TERMINAL = {"COMPLETED", "FAILED"}

# `budgetCurrency.value` → marketplace_id. The inverse of MARKETPLACE_AD_CURRENCY,
# which is what `load_ad_spend` filters on. The four currencies are distinct, so
# the mapping is total.
_CURRENCY_TO_MARKETPLACE: dict[str, str] = {c: m for m, c in MARKETPLACE_AD_CURRENCY.items()}

AD_SPEND_TABLE = "ad_spend_daily"
AD_SPEND_HISTORY_TABLE = "ad_spend_history"


def _months_in_range(start: dt.date, end: dt.date):
    """Yield (year, month) pairs from start.year-month to end.year-month inclusive."""
    y, m = start.year, start.month
    end_y, end_m = end.year, end.month
    while (y, m) <= (end_y, end_m):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def _month_bounds(y: int, m: int, cap_end: dt.date | None = None) -> tuple[dt.date, dt.date]:
    start = dt.date(y, m, 1)
    end = (dt.date(y + 1, 1, 1) if m == 12 else dt.date(y, m + 1, 1)) - dt.timedelta(days=1)
    if cap_end and end > cap_end:
        end = cap_end
    return start, end


# ── report create / poll ─────────────────────────────────────────────────────

def _submit_with_retry(client: AdsClient, advertiser_id: str, start: dt.date, end: dt.date,
                      *, initial_delay: float = 30.0, max_attempts: int = 8) -> str:
    delay = initial_delay
    for attempt in range(max_attempts):
        try:
            resp = create_probe_report(client, advertiser_id, start.isoformat(), end.isoformat(),
                                       include_currency=True)
            success = (resp.get("success") or [])
            if not success:
                raise AdsAPIError(-1, f"No success entries: {resp}")
            rid = (success[0].get("report") or {}).get("reportId")
            log.info("Submitted %s → %s → report %s", start, end, rid)
            return rid
        except AdsAPIError as exc:
            if exc.status != 429 and "429" not in str(exc):
                raise
            log.warning("429 on submit; sleeping %.0fs (attempt %d/%d)", delay, attempt + 1, max_attempts)
            time.sleep(delay)
            delay = min(600.0, delay * 1.5)
    raise AdsAPIError(-1, "Exhausted submit retries")


def _poll_report(client: AdsClient, report_id: str, *,
                interval_s: float = 45.0, max_wait_s: float = 30 * 60) -> dict[str, Any]:
    deadline = time.time() + max_wait_s
    while time.time() < deadline:
        try:
            resp = client.post("/adsApi/v1/retrieve/reports", json={"reportIds": [report_id]})
        except AdsAPIError as exc:
            if exc.status == 429:
                log.warning("429 on retrieve; sleeping 60s")
                time.sleep(60)
                continue
            raise
        entry = (resp.get("success") or [{}])[0]
        report = entry.get("report") or {}
        status = report.get("status")
        log.info("Report %s: %s", report_id, status)
        if status in _TERMINAL:
            return report
        time.sleep(interval_s)
    raise AdsAPIError(-1, f"Report {report_id} did not terminate within {max_wait_s}s")


def _download_all_parts(client: AdsClient, report: dict) -> bytes:
    parts = report.get("completedReportParts") or []
    if not parts:
        return b""
    buf = bytearray()
    for i, part in enumerate(parts):
        data = client.download(part["url"])
        if i == 0:
            buf.extend(data)
        else:
            idx = data.find(b"\n")
            buf.extend(data[idx + 1:] if idx >= 0 else data)
    return bytes(buf)


# ── persistence ──────────────────────────────────────────────────────────────

def _parse_rows(csv_bytes: bytes) -> list[dict]:
    """Every row of the report, in every currency. No filtering."""
    text = csv_bytes.decode("utf-8-sig")
    rows: list[dict] = []
    for r in csv.DictReader(io.StringIO(text)):
        rows.append({
            "date": r["date.value"],
            "campaign_id": r["campaign.id"],
            "ad_product": r["adProduct.value"],
            "budget_currency": (r.get("budgetCurrency.value") or ""),
            "total_cost": Decimal(r["metric.totalCost"]),
        })
    return rows


def _route_by_currency(rows: list[dict], marketplace_ids: list[str]) -> dict[str, list[dict]]:
    """Split report rows across marketplaces by `budgetCurrency.value`.

    Rows whose currency belongs to a marketplace we were not asked to write are
    dropped, and so are rows in a currency no marketplace claims. Both are logged:
    a silently dropped currency is how the CA/UK/AU rows went missing before.
    """
    wanted = {c: m for c, m in _CURRENCY_TO_MARKETPLACE.items() if m in marketplace_ids}
    out: dict[str, list[dict]] = {m: [] for m in marketplace_ids}
    skipped: dict[str, int] = {}
    for r in rows:
        mp = wanted.get(r["budget_currency"])
        if mp is None:
            skipped[r["budget_currency"]] = skipped.get(r["budget_currency"], 0) + 1
            continue
        out[mp].append(r)
    for currency, n in sorted(skipped.items()):
        known = currency in _CURRENCY_TO_MARKETPLACE
        log.info("  skipped %d row(s) in %s (%s)", n, currency or "<blank>",
                 "marketplace not requested" if known else "no marketplace claims this currency")
    return out


def _replace_month(conn: psycopg.Connection, marketplace_id: str,
                   month_start: dt.date, month_end: dt.date, rows: list[dict], as_of: dt.datetime,
                   table: str = AD_SPEND_TABLE,
                   history_table: str | None = AD_SPEND_HISTORY_TABLE) -> int:
    with conn.cursor() as cur:
        # Before deleting, snapshot the rows being superseded into history, with
        # `superseded_at = as_of` (the moment they stop being current). This is
        # what makes the pre-restatement state reconstructable — `as_of` on the
        # live table is a horizon only in combination with this. Skipped for
        # scratch runs (history_table=None), so verification never pollutes it.
        if history_table is not None:
            cur.execute(
                f"""
                INSERT INTO {history_table}
                    (marketplace_id, date, campaign_id, ad_product, campaign_name,
                     campaign_country, budget_currency, total_cost, updated_at, as_of, superseded_at)
                SELECT marketplace_id, date, campaign_id, ad_product, campaign_name,
                       campaign_country, budget_currency, total_cost, updated_at, as_of, %s
                FROM {table}
                WHERE marketplace_id = %s AND date >= %s AND date <= %s
                """,
                (as_of, marketplace_id, month_start, month_end),
            )
        cur.execute(
            f"DELETE FROM {table} WHERE marketplace_id = %s AND date >= %s AND date <= %s",
            (marketplace_id, month_start, month_end),
        )
        if not rows:
            conn.commit()
            return 0
        cur.executemany(
            f"""
            INSERT INTO {table}
                (marketplace_id, date, campaign_id, ad_product,
                 campaign_name, campaign_country, budget_currency, total_cost, updated_at, as_of)
            VALUES (%s, %s, %s, %s, NULL, NULL, %s, %s, now(), %s)
            ON CONFLICT (marketplace_id, date, campaign_id, ad_product) DO UPDATE SET
                budget_currency = EXCLUDED.budget_currency,
                total_cost      = EXCLUDED.total_cost,
                updated_at      = now(),
                as_of           = EXCLUDED.as_of
            """,
            [
                (marketplace_id, r["date"], r["campaign_id"], r["ad_product"],
                 r["budget_currency"], r["total_cost"], as_of)
                for r in rows
            ],
        )
    conn.commit()
    return len(rows)


# ── main sweep ───────────────────────────────────────────────────────────────

def _check_report_once(client: AdsClient, report_id: str) -> dict[str, Any] | None:
    """One /retrieve call; return terminal report dict or None if still pending."""
    try:
        resp = client.post("/adsApi/v1/retrieve/reports", json={"reportIds": [report_id]})
    except AdsAPIError as exc:
        if exc.status == 429:
            log.warning("429 on retrieve; will retry next round")
            return None
        raise
    entry = (resp.get("success") or [{}])[0]
    report = entry.get("report") or {}
    status = report.get("status")
    log.info("Report %s: %s", report_id, status)
    return report if status in _TERMINAL else None


def sweep_ad_spend(
    conn: psycopg.Connection,
    client: AdsClient,
    marketplace_ids: list[str],
    advertiser_id: str,
    *,
    start: dt.date,
    end: dt.date,
    concurrency: int = 2,
    submit_gap_s: int = 60,
    poll_round_s: int = 45,
    batch_timeout_s: int = 20 * 60,
    table: str = AD_SPEND_TABLE,
    history_table: str | None = None,
) -> dict:
    """Pull ad spend for each month in [start, end] and persist, per marketplace.

    One report per month covers every marketplace; rows are routed by
    `budgetCurrency.value`. All marketplaces in `marketplace_ids` share one
    `as_of` per month, because one pull produced them.

    Empirical rate/concurrency finding: `POST /adsApi/v1/create/reports` allows
    ~2 reports in flight at once. Attempts to submit a 3rd concurrently return
    429 for 10+ minutes. So we run **rounds of `concurrency` reports**:
    submit `concurrency`, poll them to completion, download+persist, then
    submit the next batch. Total wallclock ≈ ceil(N / concurrency) × ~10 min.
    """
    stats = {"months": 0, "submitted": 0, "completed": 0, "failed": 0, "rows": 0}
    months = list(_months_in_range(start, end))
    stats["months"] = len(months)

    remaining = list(months)
    while remaining:
        batch = remaining[:concurrency]
        remaining = remaining[concurrency:]
        # Submit this batch
        in_flight: list[tuple[str, dt.date, dt.date, str]] = []
        for y, m in batch:
            ms, me = _month_bounds(y, m, cap_end=end)
            ym = f"{y}-{m:02d}"
            log.info("Submitting %s (%s → %s)…", ym, ms, me)
            try:
                rid = _submit_with_retry(client, advertiser_id, ms, me)
            except AdsAPIError as exc:
                log.error("Submit %s permanently failed: %s", ym, exc)
                stats["failed"] += 1
                continue
            in_flight.append((ym, ms, me, rid))
            stats["submitted"] += 1
            if submit_gap_s > 0 and len(in_flight) < len(batch):
                time.sleep(submit_gap_s)

        # Poll each until terminal, download+persist. A month that never reaches
        # a terminal status is simply never written — `_replace_month` is only
        # reached on COMPLETED, so a timeout leaves that month's existing rows
        # intact rather than deleting them. Large months need headroom: 2026-01
        # (11,337 rows) exceeds the 20-minute default.
        deadline = time.time() + batch_timeout_s
        pending = list(in_flight)
        while pending and time.time() < deadline:
            still: list[tuple[str, dt.date, dt.date, str]] = []
            for ym, ms, me, rid in pending:
                report = _check_report_once(client, rid)
                if report is None:
                    still.append((ym, ms, me, rid))
                    continue
                if report.get("status") != "COMPLETED":
                    log.error("%s FAILED: %s / %s", ym,
                              report.get("failureCode"), report.get("failureReason"))
                    stats["failed"] += 1
                    continue
                data = _download_all_parts(client, report)
                rows = _parse_rows(data)
                by_mp = _route_by_currency(rows, marketplace_ids)
                # One pull, one as_of — shared across every marketplace it wrote.
                as_of = dt.datetime.now(dt.timezone.utc)
                for mp in marketplace_ids:
                    n = _replace_month(conn, mp, ms, me, by_mp[mp], as_of,
                                       table=table, history_table=history_table)
                    stats["rows"] += n
                    log.info("%s %s: %d rows persisted into %s (as_of=%s)",
                             ym, mp, n, table, as_of.isoformat())
                stats["completed"] += 1
            pending = still
            if pending:
                time.sleep(poll_round_s)
        if pending:
            log.error("Timed out with %d reports still pending in batch: %s",
                      len(pending), [p[0] for p in pending])
            stats["failed"] += len(pending)

    return stats


# ── CLI ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync.ads_spend")
    parser.add_argument("--marketplace", default="US",
                        help="US/CA/UK/AU, a literal marketplaceId, or ALL. One report covers "
                             "every marketplace; this selects which of them get written.")
    parser.add_argument("--start", default="2026-01-01", help="YYYY-MM-DD; first day of first month")
    parser.add_argument("--end", default=None, help="YYYY-MM-DD; defaults to today")
    parser.add_argument("--concurrency", type=int, default=2,
                        help="Reports in flight at once (empirical limit ≈ 2 for our account).")
    parser.add_argument("--submit-gap-s", type=int, default=60,
                        help="Seconds between submits within a batch.")
    parser.add_argument("--poll-round-s", type=int, default=45,
                        help="Seconds between poll rounds.")
    parser.add_argument("--batch-timeout-s", type=int, default=20 * 60,
                        help="How long to wait for a batch's reports. A month that times out is "
                             "left untouched, not deleted. 2026-01 needs more than the default.")
    parser.add_argument("--table", default=AD_SPEND_TABLE,
                        help="Destination table. Point at a scratch copy to verify a pull "
                             "before it touches the reconciled rows.")
    parser.add_argument("--region", default="NA")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    load_dotenv(_REPO_ROOT / ".env")
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set", file=sys.stderr)
        return 1

    if args.marketplace.upper() == "ALL":
        marketplace_ids = list(_CURRENCY_TO_MARKETPLACE.values())
    else:
        marketplace_ids = [MARKETPLACE_ALIASES.get(args.marketplace.upper(), args.marketplace)]
    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end) if args.end else dt.date.today()

    with psycopg.connect(db_url) as conn, AdsClient(region=args.region) as client:
        client.resolve_client_id_header()
        accounts = list_accounts(client)
        us = next((a.get("adsAccount") or a for a in accounts
                   if "US" in ((a.get("adsAccount") or a).get("countryCodes") or [])), None)
        if not us:
            log.error("No US account.")
            return 2
        advertiser_id = us["adsAccountId"]
        # Snapshot superseded rows to history only when writing the real table.
        # A scratch verification run leaves history untouched.
        history_table = AD_SPEND_HISTORY_TABLE if args.table == AD_SPEND_TABLE else None
        log.info("Writing %s -> %s (history: %s)", marketplace_ids, args.table, history_table)
        stats = sweep_ad_spend(conn, client, marketplace_ids, advertiser_id,
                                start=start, end=end,
                                concurrency=args.concurrency,
                                submit_gap_s=args.submit_gap_s,
                                poll_round_s=args.poll_round_s,
                                batch_timeout_s=args.batch_timeout_s,
                                table=args.table, history_table=history_table)

    log.info("Done: %d months, %d submitted, %d completed, %d failed, %d rows",
             stats["months"], stats["submitted"], stats["completed"], stats["failed"], stats["rows"])
    return 0 if stats["failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
