"""Ad-hoc multi-month puller for diagnosis (NOT the Step 2 pipeline).

Submits five report jobs in parallel (one per month), polls them together,
downloads each part, and saves the raw CSV per month to
`reference/data/ads_probe_YYYY-MM_raw.csv`.

Used only for the ADS_RESIDUAL_DIAGNOSIS.md cross-month shape check. Do NOT
extend this into the Step 2 pull — that will be built separately once the
residual is labelled.
"""

from __future__ import annotations

import argparse
import logging
import os
import pathlib
import sys
import time
from datetime import date, timedelta

from dotenv import load_dotenv

from .ads_client import AdsClient
from .ads_probe import list_accounts, create_probe_report, parse_csv

log = logging.getLogger(__name__)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

_TERMINAL = {"COMPLETED", "FAILED"}


def _month_bounds(ym: str) -> tuple[str, str]:
    year, month = map(int, ym.split("-"))
    start = date(year, month, 1)
    end = (date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)) - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _submit_all(client, advertiser_id, periods) -> dict[str, str]:
    """Return {period_ym: report_id} for each successfully submitted report."""
    out: dict[str, str] = {}
    for ym in periods:
        start, end = _month_bounds(ym)
        # /create/reports is throttled fairly aggressively; space submissions.
        for attempt in range(6):
            try:
                resp = create_probe_report(client, advertiser_id, start, end, include_currency=True)
                break
            except Exception as exc:
                if "429" in str(exc):
                    delay = 20 * (attempt + 1)
                    log.warning("429 submitting %s; sleeping %ds", ym, delay)
                    time.sleep(delay)
                    continue
                raise
        else:
            log.error("Submit %s exhausted retries", ym)
            continue
        success = (resp.get("success") or [])
        if not success:
            log.error("Submit %s failed: %s", ym, resp)
            continue
        rid = (success[0].get("report") or {}).get("reportId")
        out[ym] = rid
        log.info("Submitted %s → report %s", ym, rid)
        time.sleep(5)  # small gap to be nice to Amazon
    return out


def _poll_batch(client, report_ids: dict[str, str], interval_s: int = 30, max_wait_s: int = 30 * 60):
    """Poll a batch of report ids until each reaches a terminal status."""
    pending = dict(report_ids)  # ym → report_id
    completed: dict[str, dict] = {}   # ym → report object
    deadline = time.time() + max_wait_s
    while pending and time.time() < deadline:
        resp = client.post("/adsApi/v1/retrieve/reports", json={"reportIds": list(pending.values())})
        rid_to_ym = {v: k for k, v in pending.items()}
        for entry in (resp.get("success") or []):
            report = entry.get("report") or {}
            rid = report.get("reportId")
            status = report.get("status")
            ym = rid_to_ym.get(rid)
            log.info("Report %s (%s): %s", ym, rid, status)
            if status in _TERMINAL:
                completed[ym] = report
                pending.pop(ym, None)
        if pending:
            time.sleep(interval_s)
    if pending:
        log.error("Timed out; still pending: %s", pending)
    return completed


def _download_and_save(client, ym: str, report: dict) -> pathlib.Path | None:
    if report.get("status") != "COMPLETED":
        log.error("%s report FAILED: %s / %s", ym, report.get("failureCode"), report.get("failureReason"))
        return None
    parts = report.get("completedReportParts") or []
    if not parts:
        log.warning("%s: no parts", ym)
        return None
    # Combine parts into one CSV (headers only on first)
    out = _REPO_ROOT / "reference" / "data" / f"ads_probe_{ym}_raw.csv"
    buf = bytearray()
    for i, part in enumerate(parts):
        data = client.download(part["url"])
        if i == 0:
            buf.extend(data)
        else:
            # skip header row on subsequent parts
            idx = data.find(b"\n")
            if idx >= 0:
                buf.extend(data[idx + 1:])
    out.write_bytes(bytes(buf))
    log.info("Saved %s (%d bytes, %d parts)", out.name, len(buf), len(parts))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync.ads_multi_pull")
    parser.add_argument("--region", default="NA")
    parser.add_argument("--periods", nargs="+", default=["2026-01", "2026-03", "2026-04", "2026-05", "2026-06"])
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    load_dotenv(_REPO_ROOT / ".env")

    with AdsClient(region=args.region) as client:
        client.resolve_client_id_header()
        accounts = list_accounts(client)
        us_account = None
        for a in accounts:
            acct = a.get("adsAccount") or a
            if "US" in (acct.get("countryCodes") or []):
                us_account = acct
                break
        if not us_account:
            log.error("No US account.")
            return 2
        advertiser_id = us_account["adsAccountId"]

        report_ids = _submit_all(client, advertiser_id, args.periods)
        if not report_ids:
            log.error("Nothing submitted successfully.")
            return 2
        results = _poll_batch(client, report_ids)
        for ym, report in results.items():
            _download_and_save(client, ym, report)
    log.info("Done — %d month(s) downloaded", len(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
