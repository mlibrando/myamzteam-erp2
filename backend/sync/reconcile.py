"""Compare pnl_monthly against Sellerise's monthly response.

Reads `reference/data/SELLERISE_RAW_DATA.json` and diffs every bucket / sub-line
month-by-month against pnl_monthly. Produces a per-cell PASS/FAIL/EXPECTED
report and asserts the locked validation targets from RECONCILIATION.md Step 3.

Statuses:
- PASS      — within ±$0.01 tolerance
- FAIL      — outside tolerance
- EXPECTED  — trailing-month DEFERRED estimate line (feesObject.ReferralFee,
              fbaObject.FBAFees) — planned mismatch, not a regression

Sign conventions match Sellerise directly with one exception: our
`storageFee.storageFee` row is stored as a negative (money out via SP-API), and
Sellerise stores it as the positive magnitude. The comparator flips it.

The `expenses` bucket compares aggregate totals only — Sellerise uses
human-readable line names (`Inbound Transportation Fee`, `REVERSAL_REIMBURSEMENT`,
…) while we key by `{txn_type}.{breakdown_type}` — direct per-line matching is
not possible without a hand-maintained name map. Total-only is enough to catch
structural drift.

`adExpenses` is Ads-API (Phase 4). Until that lands the ad lines report as
OURS_MISSING and Ads-side of `net` = 0.

Usage:
    python -m sync.reconcile [--marketplace US]
                             [--output reference/data/reconcile_report.md]
                             [--log-level INFO]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import pathlib
import sys
from collections import defaultdict
from decimal import Decimal
from typing import Any

import psycopg
from dotenv import load_dotenv

from .config import MARKETPLACE_ALIASES

log = logging.getLogger(__name__)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SELLERISE_JSON = _REPO_ROOT / "reference" / "data" / "SELLERISE_RAW_DATA.json"

TOLERANCE = Decimal("0.01")

# Locked validation targets from RECONCILIATION.md Step 3.
# (bucket, sub_line, year_month, expected, decision-letter)
LOCKED_TARGETS: list[tuple[str, str, str, Decimal, str]] = [
    ("feesObject",    "ReferralFee",    "2026-02", Decimal("0.00"),   "A"),
    ("feesObject",    "ReferralFee",    "2026-03", Decimal("0.00"),   "A"),
    ("fbaObject",     "FBAFees",        "2026-02", Decimal("0.00"),   "A"),
    ("fbaObject",     "FBAFees",        "2026-03", Decimal("0.00"),   "A"),
    ("refundsObject", "RestockingFee",  "2026-02", Decimal("52.94"),  "D"),
    ("refundsObject", "RestockingFee",  "2026-04", Decimal("4.59"),   "D"),
    ("refundsObject", "RestockingFee",  "2026-06", Decimal("9.70"),   "D"),
    ("refundsObject", "Goodwill",       "2026-05", Decimal("-17.09"), "D"),
    ("refundsObject", "Goodwill",       "2026-06", Decimal("-13.23"), "D"),
    ("refundsObject", "Promotion",      "2026-02", Decimal("146.99"), "E"),
    ("refundsObject", "Promotion",      "2026-03", Decimal("44.87"),  "E"),
    ("refundsObject", "Promotion",      "2026-06", Decimal("3.99"),   "E"),
    ("chargesObject", "Promotion",      "2026-02", Decimal("-811.14"),"E"),
    ("chargesObject", "Promotion",      "2026-03", Decimal("-610.03"),"E"),
    ("chargesObject", "Promotion",      "2026-06", Decimal("-496.12"),"E"),
]

_SALES_TAX_LINES = ("Tax", "ShippingTax", "GiftWrapTax")

# Sellerise buckets are DICT (per-sub-line) vs SCALAR (top-level number).
_DICT_BUCKETS = ("chargesObject", "feesObject", "fbaObject", "refundsObject",
                 "expenses", "adExpenses")
_SCALAR_BUCKETS = ("storageFee", "cog")


# ── data loaders ────────────────────────────────────────────────────────────

def _ymd_key_to_ym(k: str) -> str:
    """'20260301' → '2026-03'."""
    return f"{k[:4]}-{k[4:6]}"


def load_sellerise(path: pathlib.Path) -> dict[str, dict[str, Any]]:
    """Return {year_month: sellerise_month_dict}."""
    raw = json.loads(path.read_text())
    return {_ymd_key_to_ym(k): v for k, v in raw.items()}


def load_pnl(conn: psycopg.Connection, marketplace_id: str) -> dict[str, dict[str, dict[str, Decimal]]]:
    """Return {year_month: {bucket: {sub_line: amount}}}."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT year_month, bucket, line_key, amount
            FROM pnl_monthly
            WHERE marketplace_id = %s
            """,
            (marketplace_id,),
        )
        rows = cur.fetchall()

    out: dict[str, dict[str, dict[str, Decimal]]] = defaultdict(lambda: defaultdict(dict))
    for ym, bucket, sub_line, amount in rows:
        out[ym][bucket][sub_line] = Decimal(str(amount))
    return out


def load_ad_spend(conn: psycopg.Connection, marketplace_id: str) -> dict[str, Decimal]:
    """Return {year_month: total_spend} from ad_spend_daily. Empty when Phase 4
    hasn't populated it yet — the audit cross-check just shows OURS_MISSING then."""
    with conn.cursor() as cur:
        try:
            cur.execute(
                """
                SELECT to_char(date, 'YYYY-MM'), SUM(total_cost)
                FROM ad_spend_daily
                WHERE marketplace_id = %s
                GROUP BY 1
                """,
                (marketplace_id,),
            )
        except psycopg.errors.UndefinedTable:
            return {}
        return {ym: Decimal(str(t)) for ym, t in cur.fetchall()}


# ── comparison primitives ───────────────────────────────────────────────────

def _status(delta: Decimal, is_trailing_estimate: bool) -> str:
    if is_trailing_estimate:
        return "EXPECTED" if abs(delta) >= TOLERANCE else "PASS"
    return "PASS" if abs(delta) < TOLERANCE else "FAIL"


def _theirs_scalar(sellerise_month: dict, bucket: str) -> Decimal:
    v = sellerise_month.get(bucket)
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def _theirs_sub_line(sellerise_month: dict, bucket: str, sub_line: str) -> Decimal:
    obj = sellerise_month.get(bucket) or {}
    v = obj.get(sub_line)
    return Decimal(str(v)) if v is not None else Decimal("0")


def _ours_scalar(pnl_month: dict, bucket: str) -> Decimal:
    """Sum all sub-lines under bucket. For storageFee flip the sign (we store
    negative money-out; Sellerise stores the positive magnitude)."""
    total = sum(pnl_month.get(bucket, {}).values(), start=Decimal("0"))
    if bucket == "storageFee":
        return -total
    return total


def _ours_sub_line(pnl_month: dict, bucket: str, sub_line: str) -> Decimal:
    return pnl_month.get(bucket, {}).get(sub_line, Decimal("0"))


# ── derived-line helpers ───────────────────────────────────────────────────

def _derive_sales_taxes(charges: dict[str, Decimal]) -> Decimal:
    return sum((charges.get(k, Decimal("0")) for k in _SALES_TAX_LINES), start=Decimal("0"))


def _compute_net_ours(
    pnl_month: dict[str, dict[str, Decimal]],
    ad_spend_total: Decimal,
    cog: Decimal,
) -> Decimal:
    """Match Sellerise's formula:
        net = revenue − salesTaxes − fees − fba − refunds − storageFee − cog − Σ adExpenses
    where fees = -Σ feesObject, etc. Sub-line stored signs match Sellerise's."""
    charges = pnl_month.get("chargesObject", {})
    revenue = sum(charges.values(), start=Decimal("0"))
    sales_taxes = _derive_sales_taxes(charges)
    fees = -sum(pnl_month.get("feesObject", {}).values(), start=Decimal("0"))
    fba = -sum(pnl_month.get("fbaObject", {}).values(), start=Decimal("0"))
    refunds = -sum(pnl_month.get("refundsObject", {}).values(), start=Decimal("0"))
    # storageFee stored negative in pnl_monthly; flip to positive magnitude
    storage = -sum(pnl_month.get("storageFee", {}).values(), start=Decimal("0"))
    return revenue - sales_taxes - fees - fba - refunds - storage - cog - ad_spend_total


def _compute_net_theirs(sellerise_month: dict) -> Decimal:
    """Same formula, sourced from Sellerise's response."""
    revenue = Decimal(str(sellerise_month.get("revenue", 0)))
    sales_taxes = Decimal(str(sellerise_month.get("salesTaxes", 0)))
    fees = Decimal(str(sellerise_month.get("fees", 0)))
    fba = Decimal(str(sellerise_month.get("fba", 0)))
    refunds = Decimal(str(sellerise_month.get("refunds", 0)))
    storage = Decimal(str(sellerise_month.get("storageFee", 0)))
    cog = Decimal(str(sellerise_month.get("cog", 0)))
    ads = sum(
        (Decimal(str(v)) for v in (sellerise_month.get("adExpenses") or {}).values()),
        start=Decimal("0"),
    )
    return revenue - sales_taxes - fees - fba - refunds - storage - cog - ads


# ── report generation ──────────────────────────────────────────────────────

def reconcile(
    conn: psycopg.Connection,
    marketplace_id: str,
    sellerise_path: pathlib.Path = SELLERISE_JSON,
) -> dict:
    sellerise_all = load_sellerise(sellerise_path)
    pnl_all = load_pnl(conn, marketplace_id)
    ad_all = load_ad_spend(conn, marketplace_id)

    # Trailing month = latest month present in Sellerise data. Only its
    # ReferralFee / FBAFees deltas are marked EXPECTED.
    months = sorted(sellerise_all.keys())
    trailing = months[-1] if months else None

    diffs: list[dict] = []

    for ym in months:
        sellerise_month = sellerise_all[ym]
        pnl_month = pnl_all.get(ym, {})

        # Union of sub-lines Sellerise has plus sub-lines we have.
        for bucket in _DICT_BUCKETS:
            their_keys = set((sellerise_month.get(bucket) or {}).keys())
            our_keys = set(pnl_month.get(bucket, {}).keys())
            if bucket == "expenses" or bucket == "adExpenses":
                # Aggregate-only compare (name mismatch on expenses; adExpenses
                # sub-lines are Ads-API and get the aggregate row).
                theirs = sum(
                    (Decimal(str(v)) for v in (sellerise_month.get(bucket) or {}).values()),
                    start=Decimal("0"),
                )
                if bucket == "adExpenses":
                    ours = ad_all.get(ym, Decimal("0")) * -1  # ad_spend is positive cost, feed into formula
                    ours_status = "OURS_MISSING" if not ad_all else _status(ours - theirs, False)
                    diffs.append({
                        "year_month": ym, "bucket": bucket, "sub_line": "(aggregate)",
                        "ours": float(ours), "theirs": float(theirs),
                        "delta": float(ours - theirs), "status": ours_status,
                    })
                else:
                    ours = sum(pnl_month.get(bucket, {}).values(), start=Decimal("0"))
                    diffs.append({
                        "year_month": ym, "bucket": bucket, "sub_line": "(aggregate)",
                        "ours": float(ours), "theirs": float(theirs),
                        "delta": float(ours - theirs), "status": _status(ours - theirs, False),
                    })
                continue

            for sub_line in sorted(their_keys | our_keys):
                ours = _ours_sub_line(pnl_month, bucket, sub_line)
                theirs = _theirs_sub_line(sellerise_month, bucket, sub_line)
                delta = ours - theirs
                is_trailing_est = (
                    ym == trailing
                    and (bucket, sub_line) in (("feesObject", "ReferralFee"), ("fbaObject", "FBAFees"))
                )
                diffs.append({
                    "year_month": ym, "bucket": bucket, "sub_line": sub_line,
                    "ours": float(ours), "theirs": float(theirs),
                    "delta": float(delta), "status": _status(delta, is_trailing_est),
                })

        # storageFee (scalar)
        ours = _ours_scalar(pnl_month, "storageFee")
        theirs = _theirs_scalar(sellerise_month, "storageFee")
        diffs.append({
            "year_month": ym, "bucket": "storageFee", "sub_line": "(scalar)",
            "ours": float(ours), "theirs": float(theirs),
            "delta": float(ours - theirs), "status": _status(ours - theirs, False),
        })

        # cog (scalar; magnitude on both sides)
        ours_cog = _ours_scalar(pnl_month, "cog")
        theirs_cog = _theirs_scalar(sellerise_month, "cog")
        diffs.append({
            "year_month": ym, "bucket": "cog", "sub_line": "(scalar)",
            "ours": float(ours_cog), "theirs": float(theirs_cog),
            "delta": float(ours_cog - theirs_cog), "status": _status(ours_cog - theirs_cog, False),
        })

        # salesTaxes (derived)
        ours_st = _derive_sales_taxes(pnl_month.get("chargesObject", {}))
        theirs_st = _theirs_scalar(sellerise_month, "salesTaxes")
        diffs.append({
            "year_month": ym, "bucket": "salesTaxes", "sub_line": "(derived)",
            "ours": float(ours_st), "theirs": float(theirs_st),
            "delta": float(ours_st - theirs_st), "status": _status(ours_st - theirs_st, False),
        })

        # net (derived, whole formula)
        ad_total = ad_all.get(ym, Decimal("0"))
        ours_net = _compute_net_ours(pnl_month, ad_total, ours_cog)
        theirs_net = _compute_net_theirs(sellerise_month)
        diffs.append({
            "year_month": ym, "bucket": "net", "sub_line": "(derived)",
            "ours": float(ours_net), "theirs": float(theirs_net),
            "delta": float(ours_net - theirs_net), "status": _status(ours_net - theirs_net, False),
        })

    # Locked-target results.
    locked_results = []
    for bucket, sub_line, ym, expected, dec in LOCKED_TARGETS:
        actual = _ours_sub_line(pnl_all.get(ym, {}), bucket, sub_line)
        delta = actual - expected
        locked_results.append({
            "decision": dec, "bucket": bucket, "sub_line": sub_line, "year_month": ym,
            "expected": float(expected), "actual": float(actual),
            "delta": float(delta), "status": "PASS" if abs(delta) < TOLERANCE else "FAIL",
        })

    # Advertising audit cross-check (decision B): SP-API AdvertisingFee vs Ads-API total.
    ad_audit = []
    for ym in months:
        sp_advert = pnl_all.get(ym, {}).get("passthrough", {})
        sp_fee = sp_advert.get("ProductAdsPayment.AdvertisingFee", Decimal("0"))
        sp_refund = sp_advert.get("ProductAdsPayment.AdvertisingFeeRefund", Decimal("0"))
        sp_total = sp_fee + sp_refund
        ads_api_total = ad_all.get(ym, Decimal("0"))
        ad_audit.append({
            "year_month": ym,
            "sp_api_advertising_fee": float(sp_total),
            "ads_api_total": float(ads_api_total),
            "delta": float(sp_total + ads_api_total),  # SP-API fee is negative, Ads-API is positive
        })

    return {
        "diffs": diffs, "locked": locked_results, "ad_audit": ad_audit,
        "trailing": trailing, "months": months,
    }


# ── output rendering ────────────────────────────────────────────────────────

def _fmt_amt(v: float) -> str:
    return f"{v:>12,.2f}"


def render_markdown(marketplace_id: str, result: dict) -> str:
    lines: list[str] = []
    lines.append(f"# Reconciliation report — marketplace {marketplace_id}")
    lines.append("")
    lines.append(f"Generated {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}.")
    lines.append(f"Trailing (DEFERRED-estimate) month: **{result['trailing']}**.")
    lines.append(f"Tolerance: ±${TOLERANCE}. Status legend: PASS · FAIL · EXPECTED (trailing-month estimate).")
    lines.append("")

    # ── Summary of counts ────────────────────────────────────────────────
    counts = defaultdict(int)
    for d in result["diffs"]:
        counts[d["status"]] += 1
    lines.append("## Summary")
    lines.append("")
    total = sum(counts.values())
    for status in ("PASS", "FAIL", "EXPECTED", "OURS_MISSING"):
        if counts[status]:
            lines.append(f"- **{status}**: {counts[status]} / {total}")
    lines.append("")

    # ── Locked validation targets ────────────────────────────────────────
    lines.append("## Locked validation targets (Step 3 assertions)")
    lines.append("")
    lines.append("| Dec. | bucket · sub_line | month | expected | actual | delta | status |")
    lines.append("|---|---|---|---:|---:|---:|---|")
    locked_pass = sum(1 for r in result["locked"] if r["status"] == "PASS")
    for r in result["locked"]:
        lines.append(
            f"| {r['decision']} | `{r['bucket']}.{r['sub_line']}` | {r['year_month']} | "
            f"{_fmt_amt(r['expected'])} | {_fmt_amt(r['actual'])} | {_fmt_amt(r['delta'])} | "
            f"{r['status']} |"
        )
    lines.append("")
    lines.append(f"**Locked targets: {locked_pass} / {len(result['locked'])} PASS**")
    lines.append("")

    # ── Ad audit cross-check (decision B) ────────────────────────────────
    lines.append("## Advertising audit cross-check (decision B)")
    lines.append("")
    lines.append("SP-API `ProductAdsPayment.AdvertisingFee` monthly total vs Ads-API `totalCost` sum.")
    lines.append("Informational: SP-API bills the money, Ads-API attributes it. Ads-side is Phase 4.")
    lines.append("")
    lines.append("| month | SP-API AdvertisingFee | Ads-API total | delta |")
    lines.append("|---|---:|---:|---:|")
    for r in result["ad_audit"]:
        lines.append(
            f"| {r['year_month']} | {_fmt_amt(r['sp_api_advertising_fee'])} | "
            f"{_fmt_amt(r['ads_api_total'])} | {_fmt_amt(r['delta'])} |"
        )
    lines.append("")

    # ── Per-month bucket diff ────────────────────────────────────────────
    by_month: dict[str, list[dict]] = defaultdict(list)
    for d in result["diffs"]:
        by_month[d["year_month"]].append(d)

    for ym in sorted(by_month.keys()):
        lines.append(f"## {ym}" + (f" (trailing DEFERRED month)" if ym == result["trailing"] else ""))
        lines.append("")
        lines.append("| bucket | sub_line | ours | theirs | delta | status |")
        lines.append("|---|---|---:|---:|---:|---|")
        rows = by_month[ym]
        rows.sort(key=lambda x: (x["bucket"], x["sub_line"]))
        for r in rows:
            lines.append(
                f"| `{r['bucket']}` | `{r['sub_line']}` | "
                f"{_fmt_amt(r['ours'])} | {_fmt_amt(r['theirs'])} | "
                f"{_fmt_amt(r['delta'])} | {r['status']} |"
            )
        lines.append("")

    return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync.reconcile")
    parser.add_argument("--marketplace", default="US")
    parser.add_argument(
        "--output",
        default=str(_REPO_ROOT / "reference" / "data" / "reconcile_report.md"),
        help="Markdown output path",
    )
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

    with psycopg.connect(db_url) as conn:
        result = reconcile(conn, marketplace_id)

    pathlib.Path(args.output).write_text(render_markdown(marketplace_id, result))
    log.info("Wrote %s — %d cells across %d months", args.output, len(result["diffs"]), len(result["months"]))

    # Summary logging
    counts: dict[str, int] = defaultdict(int)
    for d in result["diffs"]:
        counts[d["status"]] += 1
    locked_pass = sum(1 for r in result["locked"] if r["status"] == "PASS")
    log.info(
        "Cell counts: %s. Locked targets: %d/%d PASS",
        dict(counts), locked_pass, len(result["locked"]),
    )

    # Exit 0 if all PASS + all locked targets PASS; else 1.
    all_good = counts.get("FAIL", 0) == 0 and locked_pass == len(result["locked"])
    return 0 if all_good else 1


if __name__ == "__main__":
    raise SystemExit(main())
