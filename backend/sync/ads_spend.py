"""Amazon Ads monthly-spend pull → ad_spend_daily.

Per Phase-4 Step-2 design: one report per month, `date.value` + `campaign.id` +
`adProduct.value` + `budgetCurrency.value` + `metric.totalCost`, USD filter,
persisted with a per-row `as_of` timestamp.

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

Usage:
    python -m sync.ads_spend [--marketplace US] [--start 2026-01-01]
                             [--end YYYY-MM-DD] [--parallel-submit 1]
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
from .config import MARKETPLACE_ALIASES, US_MARKETPLACE_ID

log = logging.getLogger(__name__)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

_TERMINAL = {"COMPLETED", "FAILED"}


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

def _parse_and_filter_usd(csv_bytes: bytes) -> list[dict]:
    text = csv_bytes.decode("utf-8-sig")
    rows: list[dict] = []
    for r in csv.DictReader(io.StringIO(text)):
        if (r.get("budgetCurrency.value") or "") != "USD":
            continue
        rows.append({
            "date": r["date.value"],
            "campaign_id": r["campaign.id"],
            "ad_product": r["adProduct.value"],
            "budget_currency": r["budgetCurrency.value"],
            "total_cost": Decimal(r["metric.totalCost"]),
        })
    return rows


def _replace_month(conn: psycopg.Connection, marketplace_id: str,
                   month_start: dt.date, month_end: dt.date, rows: list[dict], as_of: dt.datetime) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM ad_spend_daily WHERE marketplace_id = %s AND date >= %s AND date <= %s",
            (marketplace_id, month_start, month_end),
        )
        if not rows:
            conn.commit()
            return 0
        cur.executemany(
            """
            INSERT INTO ad_spend_daily
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
    marketplace_id: str,
    advertiser_id: str,
    *,
    start: dt.date,
    end: dt.date,
    concurrency: int = 2,
    submit_gap_s: int = 60,
    poll_round_s: int = 45,
) -> dict:
    """Pull ad spend for each month in [start, end] and persist.

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

        # Poll each until terminal, download+persist
        deadline = time.time() + 20 * 60  # 20 min per batch cap
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
                usd_rows = _parse_and_filter_usd(data)
                as_of = dt.datetime.now(dt.timezone.utc)
                n = _replace_month(conn, marketplace_id, ms, me, usd_rows, as_of)
                stats["completed"] += 1
                stats["rows"] += n
                log.info("%s: %d USD rows persisted (as_of=%s)", ym, n, as_of.isoformat())
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
    parser.add_argument("--marketplace", default="US")
    parser.add_argument("--start", default="2026-01-01", help="YYYY-MM-DD; first day of first month")
    parser.add_argument("--end", default=None, help="YYYY-MM-DD; defaults to today")
    parser.add_argument("--concurrency", type=int, default=2,
                        help="Reports in flight at once (empirical limit ≈ 2 for our account).")
    parser.add_argument("--submit-gap-s", type=int, default=60,
                        help="Seconds between submits within a batch.")
    parser.add_argument("--poll-round-s", type=int, default=45,
                        help="Seconds between poll rounds.")
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

    marketplace_id = MARKETPLACE_ALIASES.get(args.marketplace.upper(), args.marketplace)
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
        stats = sweep_ad_spend(conn, client, marketplace_id, advertiser_id,
                                start=start, end=end,
                                concurrency=args.concurrency,
                                submit_gap_s=args.submit_gap_s,
                                poll_round_s=args.poll_round_s)

    log.info("Done: %d months, %d submitted, %d completed, %d failed, %d rows",
             stats["months"], stats["submitted"], stats["completed"], stats["failed"], stats["rows"])
    return 0 if stats["failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
