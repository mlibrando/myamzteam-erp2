"""Ads-API probe (Phase 4 V1/V2 verification).

Empirically resolves the questions the plan requires before writing the full pull:
- Which `Amazon-*-ClientId` header actually works?
- What is the exact `advertiserAccountId` for the US account?
- Does the report endpoint accept `accessRequestedAccounts` per docs?
- What distinct `adProduct.value` strings come back?
- What is the denomination of `metric.totalCost` (units vs micros)?
- Is `budgetCurrency.value` needed to get `totalCost`?
- Does SB Video appear as a distinct value anywhere?

Dumps everything to `reference/data/ads_probe.md` for review before Step 2.

Usage:
    python -m sync.ads_probe [--region NA] [--period 2026-02]
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import os
import pathlib
import sys
import time
from collections import Counter
from decimal import Decimal
from typing import Any

from dotenv import load_dotenv

from .ads_client import AdsClient, AdsAPIError

log = logging.getLogger(__name__)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PROBE_OUT = _REPO_ROOT / "reference" / "data" / "ads_probe.md"

_TERMINAL_STATUSES = {"COMPLETED", "FAILED"}


def list_accounts(client: AdsClient) -> list[dict[str, Any]]:
    resp = client.post("/adsAccounts/list")
    # Response shape per docs: top-level list of {adsAccount: {...}}.
    # Some versions wrap in a dict with "adsAccounts" key — handle both.
    if isinstance(resp, list):
        return resp
    return resp.get("adsAccounts") or []


def create_probe_report(
    client: AdsClient,
    advertiser_account_id: str,
    start_date: str,
    end_date: str,
    include_currency: bool,
) -> dict[str, Any]:
    # `metric.totalCost` needs `budgetCurrency.value`, and the API also requires
    # at least one "level-of-detail" primary key (empirical: adProduct.value
    # alone isn't enough — needs campaign.id). Bake both in and record the
    # rejection message when we probe without them.
    fields = ["date.value", "campaign.id", "adProduct.value", "metric.totalCost"]
    if include_currency:
        fields.append("budgetCurrency.value")
    body = {
        "accessRequestedAccounts": [{"advertiserAccountId": advertiser_account_id}],
        "reports": [
            {
                "format": "CSV",
                "periods": [
                    {"datePeriod": {"startDate": start_date, "endDate": end_date}}
                ],
                "query": {"fields": fields},
            }
        ],
    }
    return client.post("/adsApi/v1/create/reports", json=body)


def poll_report(client: AdsClient, report_id: str, poll_interval_s: float = 30.0,
                max_wait_s: float = 20 * 60.0) -> dict[str, Any]:
    """Poll until report reaches terminal status. Returns final report object."""
    deadline = time.time() + max_wait_s
    while time.time() < deadline:
        resp = client.post("/adsApi/v1/retrieve/reports", json={"reportIds": [report_id]})
        success = (resp.get("success") or [])
        if not success:
            raise AdsAPIError(-1, f"No success entries in retrieve response: {resp}")
        report = success[0].get("report") or {}
        status = report.get("status")
        log.info("Report %s status: %s", report_id, status)
        if status in _TERMINAL_STATUSES:
            return report
        time.sleep(poll_interval_s)
    raise AdsAPIError(-1, f"Timed out waiting for report {report_id}")


def parse_csv(csv_bytes: bytes) -> tuple[list[str], list[dict[str, str]]]:
    text = csv_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    return (reader.fieldnames or []), rows


def _fmt_amt(v: float) -> str:
    return f"{v:>14,.2f}"


def probe(region: str, ym: str) -> int:
    year, month = map(int, ym.split("-"))
    # Choose start / end for the month.
    from datetime import date, timedelta

    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)

    findings: list[str] = []
    findings.append(f"# Ads-API probe — region {region}, period {ym}")
    findings.append("")
    findings.append(f"Window: `{start}` → `{end}` (inclusive).")
    findings.append("")

    with AdsClient(region=region) as client:
        # 1. Resolve ClientId header
        header = client.resolve_client_id_header()
        findings.append("## ClientId header (empirical)")
        findings.append("")
        findings.append(f"- Accepted header name: **`{header}`**")
        findings.append(f"- Tried: {list(client.CLIENT_ID_HEADER_CANDIDATES if hasattr(client, 'CLIENT_ID_HEADER_CANDIDATES') else ['Amazon-Ads-ClientId', 'Amazon-Advertising-API-ClientId'])}")
        findings.append("")

        # 2. List accounts
        accounts = list_accounts(client)
        findings.append("## Accounts")
        findings.append("")
        findings.append(f"`/adsAccounts/list` returned {len(accounts)} account(s).")
        for a in accounts:
            acct = a.get("adsAccount") or a
            findings.append(
                f"- **{acct.get('accountName') or acct.get('adsAccountId')}** "
                f"— id=`{acct.get('adsAccountId')}` status=`{acct.get('status')}` "
                f"countries={acct.get('countryCodes')}"
            )
        findings.append("")

        us_account = None
        for a in accounts:
            acct = a.get("adsAccount") or a
            if "US" in (acct.get("countryCodes") or []):
                us_account = acct
                break
        if not us_account:
            findings.append("**FATAL**: no US account found — cannot probe.")
            _PROBE_OUT.write_text("\n".join(findings))
            return 2
        advertiser_id = us_account["adsAccountId"]
        findings.append(f"US `advertiserAccountId`: `{advertiser_id}`")
        findings.append("")

        # 3. Create report, first WITHOUT budgetCurrency
        findings.append("## Create report — probe A (no `budgetCurrency.value`)")
        findings.append("")
        try:
            resp = create_probe_report(
                client, advertiser_id, start.isoformat(), end.isoformat(),
                include_currency=False,
            )
            probe_a_ok = True
        except AdsAPIError as exc:
            findings.append(f"- Failed: {exc}")
            probe_a_ok = False
            resp = None

        include_currency = False
        report_id = None
        if probe_a_ok:
            success = (resp.get("success") or [])
            errors = (resp.get("error") or resp.get("errors") or [])
            findings.append(f"- Response `success` entries: {len(success)}; `error`: {errors}")
            if success:
                report = success[0].get("report") or {}
                report_id = report.get("reportId")
                status = report.get("status")
                findings.append(f"- Report id: `{report_id}`, initial status: `{status}`")
            else:
                probe_a_ok = False

        # 4. If probe A failed, try WITH budgetCurrency
        if not probe_a_ok:
            findings.append("")
            findings.append("## Create report — probe B (with `budgetCurrency.value`)")
            findings.append("")
            try:
                resp = create_probe_report(
                    client, advertiser_id, start.isoformat(), end.isoformat(),
                    include_currency=True,
                )
                success = (resp.get("success") or [])
                if success:
                    report = success[0].get("report") or {}
                    report_id = report.get("reportId")
                    findings.append(f"- Success with `budgetCurrency.value`. Report id: `{report_id}`")
                    include_currency = True
                else:
                    findings.append(f"- Failed: {resp}")
                    _PROBE_OUT.write_text("\n".join(findings))
                    return 2
            except AdsAPIError as exc:
                findings.append(f"- Failed: {exc}")
                _PROBE_OUT.write_text("\n".join(findings))
                return 2

        findings.append("")
        findings.append(f"**`budgetCurrency.value` required for `totalCost`?** "
                        f"{'yes' if include_currency else 'no'}")
        findings.append("")

        # 5. Poll to completion
        findings.append("## Poll to completion")
        findings.append("")
        report = poll_report(client, report_id)
        findings.append(f"- Final status: `{report.get('status')}`")
        if report.get("status") != "COMPLETED":
            findings.append(f"- failureCode: `{report.get('failureCode')}`")
            findings.append(f"- failureReason: `{report.get('failureReason')}`")
            _PROBE_OUT.write_text("\n".join(findings))
            return 2

        parts = report.get("completedReportParts") or []
        findings.append(f"- {len(parts)} part(s) to download.")
        findings.append("")

        # 6. Download + parse
        all_rows: list[dict[str, str]] = []
        raw_csv_out = _REPO_ROOT / "reference" / "data" / f"ads_probe_{ym}_raw.csv"
        for i, part in enumerate(parts):
            data = client.download(part["url"])
            headers, rows = parse_csv(data)
            findings.append(f"### Part {i} — {len(rows)} rows, headers = {headers}")
            findings.append("")
            all_rows.extend(rows)
            if i == 0:
                raw_csv_out.write_bytes(data)
                findings.append(f"Raw CSV saved to `{raw_csv_out.relative_to(_REPO_ROOT)}`.")
                findings.append("")

        # 7. Analyse
        findings.append("## adProduct distinct values")
        findings.append("")
        ad_products = Counter(r.get("adProduct") or r.get("adProduct.value") or "" for r in all_rows)
        findings.append("| adProduct | rows |")
        findings.append("|---|---:|")
        for ap, n in ad_products.most_common():
            findings.append(f"| `{ap}` | {n} |")
        findings.append("")
        sb_video_present = any("VIDEO" in (ap or "").upper() for ap in ad_products)
        findings.append(f"**SB Video visible in `adProduct`?** "
                        f"{'YES' if sb_video_present else 'NO (must merge into SB for hsaCost+hsaVideoCost)'}")
        findings.append("")

        # 8. totalCost denomination — sum for the month vs Sellerise
        findings.append("## `metric.totalCost` denomination")
        findings.append("")
        total_by_product: dict[str, Decimal] = {}
        for r in all_rows:
            ap = r.get("adProduct") or r.get("adProduct.value") or ""
            cost_str = (r.get("totalCost") or r.get("metric.totalCost") or "0").strip()
            try:
                total_by_product[ap] = total_by_product.get(ap, Decimal("0")) + Decimal(cost_str)
            except Exception:
                pass
        grand_total = sum(total_by_product.values(), Decimal("0"))
        findings.append(f"- Total (raw units) for {ym}: **{grand_total}**")

        # Compare to Sellerise
        sellerise_json = _REPO_ROOT / "reference" / "data" / "SELLERISE_RAW_DATA.json"
        try:
            sd = json.loads(sellerise_json.read_text())
            key = ym.replace("-", "") + "01"
            sm = sd.get(key, {})
            adx = sm.get("adExpenses") or {}
            sellerise_total = sum(Decimal(str(v)) for v in adx.values() if v is not None)
            findings.append(f"- Sellerise `adExpenses` total for {ym}: **{sellerise_total}**")
            if sellerise_total:
                ratio = grand_total / sellerise_total
                findings.append(f"- Ratio ours / Sellerise: **{ratio:.6f}**")
                if abs(ratio - 1) < 0.01:
                    denom = "currency units (USD, matches Sellerise)"
                elif abs(ratio - 1_000_000) < 100_000:
                    denom = "MICROS (÷ 1,000,000 to match Sellerise)"
                else:
                    denom = f"UNKNOWN — ratio {ratio}, investigate"
                findings.append(f"- **Denomination verdict**: {denom}")
        except Exception as exc:
            findings.append(f"- Sellerise comparison failed: {exc}")

        findings.append("")
        findings.append("## Per-product monthly totals — ALL currencies (raw units, ours)")
        findings.append("")
        findings.append("| adProduct | total (raw) |")
        findings.append("|---|---:|")
        for ap, tot in sorted(total_by_product.items()):
            findings.append(f"| `{ap}` | {tot} |")
        findings.append("")

        # USD-only breakdown per plan ("US only, USD, no FX")
        usd_by_product: dict[str, Decimal] = {}
        currency_counts: Counter[str] = Counter()
        for r in all_rows:
            cur = (r.get("budgetCurrency") or r.get("budgetCurrency.value") or "").strip()
            currency_counts[cur] += 1
            if cur != "USD":
                continue
            ap = r.get("adProduct") or r.get("adProduct.value") or ""
            cost_str = (r.get("totalCost") or r.get("metric.totalCost") or "0").strip()
            try:
                usd_by_product[ap] = usd_by_product.get(ap, Decimal("0")) + Decimal(cost_str)
            except Exception:
                pass
        findings.append("## `budgetCurrency.value` distribution (row counts)")
        findings.append("")
        for cur, n in currency_counts.most_common():
            findings.append(f"- `{cur or '(blank)'}`: {n}")
        findings.append("")

        findings.append("## Per-product monthly totals — USD ONLY")
        findings.append("")
        findings.append("| adProduct | total USD |")
        findings.append("|---|---:|")
        for ap, tot in sorted(usd_by_product.items()):
            findings.append(f"| `{ap}` | {tot} |")
        usd_total = sum(usd_by_product.values(), Decimal("0"))
        findings.append(f"| **TOTAL USD** | **{usd_total}** |")
        findings.append("")

        # Comparison per line vs Sellerise 5-line map (SB Video merged into SB)
        try:
            sd = json.loads((_REPO_ROOT / "reference" / "data" / "SELLERISE_RAW_DATA.json").read_text())
            key = ym.replace("-", "") + "01"
            adx = (sd.get(key, {}).get("adExpenses") or {})
            s_adCost = Decimal(str(adx.get("adCost", 0) or 0))
            s_hsaCost = Decimal(str(adx.get("hsaCost", 0) or 0))
            s_hsaVideoCost = Decimal(str(adx.get("hsaVideoCost", 0) or 0))
            s_sdCost = Decimal(str(adx.get("sdCost", 0) or 0))
            s_stvCost = Decimal(str(adx.get("stvCost", 0) or 0))
            our_sp = usd_by_product.get("Sponsored Products", Decimal("0"))
            our_sb = usd_by_product.get("Sponsored Brands", Decimal("0"))
            our_sd = usd_by_product.get("Sponsored Display", Decimal("0"))
            findings.append("## V1 Sellerise 5-line comparison — USD-only (SB Video merged into SB)")
            findings.append("")
            findings.append("| Sellerise line | ours (USD) | Sellerise | delta |")
            findings.append("|---|---:|---:|---:|")
            findings.append(f"| adCost (Sponsored Products) | {our_sp} | {s_adCost} | {our_sp - s_adCost} |")
            findings.append(f"| hsaCost + hsaVideoCost (Sponsored Brands+Video, merged) | {our_sb} | {s_hsaCost + s_hsaVideoCost} | {our_sb - (s_hsaCost + s_hsaVideoCost)} |")
            findings.append(f"| sdCost (Sponsored Display) | {our_sd} | {s_sdCost} | {our_sd - s_sdCost} |")
            findings.append(f"| stvCost (Sponsored TV) | 0 (absent from probe) | {s_stvCost} | {-s_stvCost} |")
            findings.append(f"| **TOTAL** | **{our_sp + our_sb + our_sd}** | **{s_adCost + s_hsaCost + s_hsaVideoCost + s_sdCost + s_stvCost}** | **{our_sp + our_sb + our_sd - (s_adCost + s_hsaCost + s_hsaVideoCost + s_sdCost + s_stvCost)}** |")
            findings.append("")
        except Exception as exc:
            findings.append(f"Sellerise comparison failed: {exc}")

        # 9. Sample rows
        findings.append("## Sample rows (first 8)")
        findings.append("")
        findings.append("```")
        for r in all_rows[:8]:
            findings.append(json.dumps(r))
        findings.append("```")
        findings.append("")

    _PROBE_OUT.parent.mkdir(parents=True, exist_ok=True)
    _PROBE_OUT.write_text("\n".join(findings))
    log.info("Probe report written to %s", _PROBE_OUT)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync.ads_probe")
    parser.add_argument("--region", default="NA")
    parser.add_argument("--period", default="2026-02", help="YYYY-MM settled month to probe")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    load_dotenv(_REPO_ROOT / ".env")
    return probe(args.region, args.period)


if __name__ == "__main__":
    raise SystemExit(main())
