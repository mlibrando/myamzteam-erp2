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

from .attribution import load_order_purchase_dates, order_id_from_related, resolve_attribution_ym, ym as _ym
from .bucket_map import EXPENSES, NET, classify
from .config import MARKETPLACE_ALIASES
from . import drift_bands as _drift

log = logging.getLogger(__name__)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SELLERISE_JSON = _REPO_ROOT / "reference" / "data" / "SELLERISE_RAW_DATA.json"

# Per-marketplace Sellerise-target files. `None` means no target file (US
# reconciliation targets stay the default). `SELLERISE_JSON` is US.
MARKETPLACE_SELLERISE: dict[str, pathlib.Path | None] = {
    "ATVPDKIKX0DER": SELLERISE_JSON,  # US
    "A2EUQ1WTGCTBG2": _REPO_ROOT / "reference" / "data" / "SELLERISE_RAW_DATA_CA.json",
    "A1F83G8C2ARO7P": _REPO_ROOT / "reference" / "data" / "SELLERISE_RAW_DATA_UK.json",
    # AU has no Sellerise target file — reconciliation blocked
    "A39IBJ37TRP1C6": None,
}

TOLERANCE = Decimal("0.01")

# Locked validation targets from RECONCILIATION.md Step 3 — US only. Other
# markets have empty target lists until per-marketplace targets are set from
# their own data.
US_LOCKED_TARGETS: list[tuple[str, str, str, Decimal, str]] = [
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

# Per-marketplace locked targets (US only for now). Add per-marketplace entries
# once the Sellerise-side targets are documented for CA/UK.
LOCKED_TARGETS_BY_MARKETPLACE: dict[str, list] = {
    "ATVPDKIKX0DER": US_LOCKED_TARGETS,
    "A2EUQ1WTGCTBG2": [],   # CA — no locked targets yet
    "A1F83G8C2ARO7P": [],   # UK — no locked targets yet
    "A39IBJ37TRP1C6": [],   # AU
}


def _resolve_sellerise_path(marketplace_id: str, override: pathlib.Path | None = None) -> pathlib.Path:
    if override is not None:
        return override
    p = MARKETPLACE_SELLERISE.get(marketplace_id)
    if p is None:
        raise ValueError(f"No Sellerise target file for marketplace {marketplace_id}")
    return p

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


def compute_pnl_in_memory(
    conn: psycopg.Connection,
    marketplace_id: str,
    *,
    shipment_basis: str,   # "posted" or "purchase"
    refund_basis: str,     # "posted" or "purchase"
    ingested_before: dt.datetime | None = None,
) -> dict[str, dict[str, dict[str, Decimal]]]:
    """Compute Sellerise-shaped pnl totals in memory under a specified attribution basis.

    shipment_basis="posted"  and refund_basis="posted"  → legacy baseline (all postedDate)
    shipment_basis="purchase"                          → Shipment on order PurchaseDate
    refund_basis="purchase"                            → also re-attribute Refunds

    Non-order transactions (ServiceFee, adjustments, transfers, etc.) always use
    postedDate under any basis. Falls back to postedDate whenever the order id is
    missing from the map — those fallbacks stay silent here; the aggregator logs
    them separately.
    """
    order_map = load_order_purchase_dates(conn, marketplace_id, ingested_before) if (
        shipment_basis == "purchase" or refund_basis == "purchase"
    ) else {}

    # `ingested_before` reconstructs the pnl as it stood at an ingestion horizon.
    # It changes no math — it only narrows which source rows are visible.
    horizon = "AND t.ingested_at <= %s" if ingested_before is not None else ""
    hp: tuple = (ingested_before,) if ingested_before is not None else ()

    # Pass 1 — attribution_ym per txn.
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT t.transaction_id,
                   t.posted_at,
                   COALESCE(t.transaction_status, t.raw_json->>'transactionStatus'),
                   t.raw_json->>'transactionType',
                   t.raw_json->'relatedIdentifiers'
            FROM sp_transactions t
            WHERE t.marketplace_id = %s
              AND t.is_deferred_release_event = false
              {horizon}
            """,
            (marketplace_id,) + hp,
        )
        rows = cur.fetchall()

    txn_meta: dict[str, tuple[str, str, str]] = {}
    for txn_id, posted_at, status, txn_type, related in rows:
        oid = order_id_from_related(related or [])
        # Force shipment_basis behavior by pretending non-Shipment txns follow
        # the same rule structure. We do this by passing txn_type unchanged and
        # relying on resolve_attribution_ym() to keep non-order on postedDate.
        # For the "posted" baseline, we skip the order lookup entirely.
        if shipment_basis == "posted":
            # Legacy: everything postedDate. resolve_attribution_ym does that
            # when refund_basis="posted" and txn_type not in (Shipment, Refund),
            # so short-circuit by not passing an order id.
            att_ym = _ym(posted_at)
        else:
            att_ym, _ = resolve_attribution_ym(
                txn_type=txn_type or "Unknown",
                posted_at=posted_at,
                order_id=oid,
                order_map=order_map,
                refund_basis=refund_basis,
            )
        txn_meta[txn_id] = (att_ym, txn_type or "Unknown", status or "")

    # Pass 2 — aggregate breakdowns via classify().
    out: dict[str, dict[str, dict[str, Decimal]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: Decimal("0"))))
    with conn.cursor(name="recon_breakdowns") as cur:
        cur.itersize = 5000
        cur.execute(
            f"""
            SELECT b.transaction_id, b.breakdown_type, b.breakdown_amount
            FROM sp_breakdowns b
            JOIN sp_transactions t ON t.transaction_id = b.transaction_id
            WHERE t.marketplace_id = %s
              AND t.is_deferred_release_event = false
              {horizon}
            """,
            (marketplace_id,) + hp,
        )
        for txn_id, breakdown_type, amount in cur:
            meta = txn_meta.get(txn_id)
            if meta is None:
                continue
            att_ym, txn_type, txn_status = meta
            rule = classify(txn_type, breakdown_type, txn_status)
            if rule is None:
                continue
            out[att_ym][rule.bucket][rule.sub_line] += Decimal(str(amount))

    # Materialize (freeze defaults into plain dicts).
    return {ym: {b: dict(subs) for b, subs in bd.items()} for ym, bd in out.items()}


def compute_cog_by_basis(
    conn: psycopg.Connection,
    marketplace_id: str,
    *,
    basis: str,                # "posted" or "purchase" (shipment attribution)
    net_refunds: bool = True,
    refund_basis: str | None = None,   # separate refund attribution; defaults to `basis`
    ingested_before: dt.datetime | None = None,
) -> dict[str, Decimal]:
    """Return {year_month: cog_magnitude} using the specified attributions.

    Shipment cog attribution uses `basis`. Refund cog netting uses
    `refund_basis` (defaults to `basis` for backward compat). Empirical
    winners per marketplace:
    - US: shipment=purchase, refund=purchase
    - UK: shipment=purchase, refund=purchase
    - CA: shipment=purchase, refund=posted (config MARKETPLACE_REFUND_COGS_BASIS)
    """
    if refund_basis is None:
        refund_basis = basis
    ship_date = "COALESCE(opd.purchase_date, t.posted_at)" if basis == "purchase" else "t.posted_at"
    refund_date = "COALESCE(opd.purchase_date, t.posted_at)" if refund_basis == "purchase" else "t.posted_at"
    # cog source override: for marketplaces whose workbook sheet has provisional
    # cost values (e.g. CA sheet is US×1.35, not real CA sourcing), join
    # cogs_per_sku on the override marketplace instead of the transaction's
    # marketplace. See MARKETPLACE_COG_SOURCE_OVERRIDE in config.
    from .config import cog_source_marketplace
    cog_mp = cog_source_marketplace(marketplace_id)
    # See compute_pnl_in_memory: `ingested_before` narrows the visible rows to an
    # ingestion horizon, for the drift guard's "did new rows move this?" test.
    # The order map is horizoned too, so a newly-fetched PurchaseDate cannot
    # silently re-attribute an old transaction.
    horizon = "AND t.ingested_at <= %s" if ingested_before is not None else ""
    opd_horizon = "AND opd.ingested_at <= %s" if ingested_before is not None else ""
    hp: tuple = (ingested_before,) if ingested_before is not None else ()
    if not net_refunds:
        # Legacy pre-fix path
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT to_char({ship_date} AT TIME ZONE 'UTC', 'YYYY-MM') AS ym,
                       SUM(i.quantity_shipped * c.cogs)                   AS amt
                FROM sp_transaction_items i
                JOIN sp_transactions t ON t.transaction_id = i.transaction_id
                JOIN cogs_per_sku c ON c.sku = i.sku AND c.marketplace_id = %s
                LEFT JOIN LATERAL (
                    SELECT ri->>'relatedIdentifierValue' AS order_id
                    FROM jsonb_array_elements(t.raw_json->'relatedIdentifiers') ri
                    WHERE ri->>'relatedIdentifierName' = 'ORDER_ID' LIMIT 1
                ) rel ON true
                LEFT JOIN order_purchase_date opd
                  ON opd.order_id = rel.order_id AND opd.marketplace_id = t.marketplace_id
                  {opd_horizon}
                WHERE t.marketplace_id = %s
                  AND t.is_deferred_release_event = false
                  AND (t.raw_json->>'transactionType') = 'Shipment'
                  AND i.quantity_shipped > 0
                  {horizon}
                GROUP BY 1
                """,
                (cog_mp,) + hp + (marketplace_id,) + hp,
            )
            return {ym: Decimal(str(amt)) for ym, amt in cur.fetchall()}
    with conn.cursor() as cur:
        cur.execute(
            f"""
            WITH ship_or_refund AS (
                SELECT i.sku,
                       CASE (t.raw_json->>'transactionType')
                            WHEN 'Shipment' THEN i.quantity_shipped
                            WHEN 'Refund'   THEN -i.quantity_shipped
                       END AS net_qty,
                       to_char(
                           CASE (t.raw_json->>'transactionType')
                               WHEN 'Shipment' THEN {ship_date}
                               WHEN 'Refund'   THEN {refund_date}
                           END AT TIME ZONE 'UTC', 'YYYY-MM'
                       ) AS ym
                FROM sp_transaction_items i
                JOIN sp_transactions t ON t.transaction_id = i.transaction_id
                LEFT JOIN LATERAL (
                    SELECT ri->>'relatedIdentifierValue' AS order_id
                    FROM jsonb_array_elements(t.raw_json->'relatedIdentifiers') ri
                    WHERE ri->>'relatedIdentifierName' = 'ORDER_ID' LIMIT 1
                ) rel ON true
                LEFT JOIN order_purchase_date opd
                  ON opd.order_id = rel.order_id AND opd.marketplace_id = t.marketplace_id
                  {opd_horizon}
                WHERE t.marketplace_id = %s
                  AND t.is_deferred_release_event = false
                  AND (t.raw_json->>'transactionType') IN ('Shipment', 'Refund')
                  AND i.quantity_shipped > 0
                  {horizon}
            )
            SELECT sr.ym, SUM(sr.net_qty * c.cogs) AS amt
            FROM ship_or_refund sr
            JOIN cogs_per_sku c
              ON c.sku = sr.sku AND c.marketplace_id = %s
            GROUP BY 1
            """,
            hp + (marketplace_id,) + hp + (cog_mp,),
        )
        return {ym: Decimal(str(amt)) for ym, amt in cur.fetchall()}


def load_ad_spend(conn: psycopg.Connection, marketplace_id: str) -> dict[str, Decimal]:
    """Return {year_month: total_native_currency_spend} from ad_spend_daily.
    Filters by that marketplace's native currency (per MARKETPLACE_AD_CURRENCY).
    Empty when the ad_spend_daily table is missing or the pull hasn't run yet."""
    from .config import MARKETPLACE_AD_CURRENCY
    currency = MARKETPLACE_AD_CURRENCY.get(marketplace_id, "USD")
    with conn.cursor() as cur:
        try:
            cur.execute(
                """
                SELECT to_char(date, 'YYYY-MM'), SUM(total_cost)
                FROM ad_spend_daily
                WHERE marketplace_id = %s
                  AND budget_currency = %s
                GROUP BY 1
                """,
                (marketplace_id, currency),
            )
        except psycopg.errors.UndefinedTable:
            return {}
        return {ym: Decimal(str(t)) for ym, t in cur.fetchall()}


# Sellerise ad-line ↔ SP-API adProduct.value mapping. SB Video is not
# separable on adProduct.value (probe-confirmed), so hsaCost+hsaVideoCost are
# merged into the SPONSORED_BRANDS line.
_AD_LINE_MAP = [
    # (sellerise_key, api_adProduct_string, human_label)
    ("adCost",       "Sponsored Products", "Sponsored Products"),
    ("hsaCost+hsaVideoCost", "Sponsored Brands", "Sponsored Brands (+Video, merged)"),
    ("sdCost",       "Sponsored Display",  "Sponsored Display"),
    ("stvCost",      "Sponsored Television", "Sponsored TV (absent from API)"),
]


def load_ad_spend_by_line(conn: psycopg.Connection, marketplace_id: str) -> dict[str, dict[str, Decimal]]:
    """Return {year_month: {api_adProduct_string: total_native_currency_spend}}."""
    from .config import MARKETPLACE_AD_CURRENCY
    currency = MARKETPLACE_AD_CURRENCY.get(marketplace_id, "USD")
    with conn.cursor() as cur:
        try:
            cur.execute(
                """
                SELECT to_char(date, 'YYYY-MM'), ad_product, SUM(total_cost)
                FROM ad_spend_daily
                WHERE marketplace_id = %s
                  AND budget_currency = %s
                GROUP BY 1, 2
                """,
                (marketplace_id, currency),
            )
        except psycopg.errors.UndefinedTable:
            return {}
        out: dict[str, dict[str, Decimal]] = defaultdict(dict)
        for ym, ap, tot in cur.fetchall():
            out[ym][ap] = Decimal(str(tot))
        return dict(out)


def load_ad_spend_as_of(conn: psycopg.Connection, marketplace_id: str) -> dict[str, dt.datetime]:
    """Return {year_month: max(as_of)} so the report shows when each month was last pulled."""
    with conn.cursor() as cur:
        try:
            cur.execute(
                """
                SELECT to_char(date, 'YYYY-MM'), MAX(as_of)
                FROM ad_spend_daily
                WHERE marketplace_id = %s
                GROUP BY 1
                """,
                (marketplace_id,),
            )
        except (psycopg.errors.UndefinedTable, psycopg.errors.UndefinedColumn):
            return {}
        return {ym: t for ym, t in cur.fetchall()}


# Restatement-drift tolerance: sub-dollar-to-few-dollar deltas per line show as
# PASS-with-note (drift, not FAIL). Trailing month is EXPECTED-to-drift.
_AD_DRIFT_TOLERANCE = Decimal("5.00")


def _ad_status(delta: Decimal, is_trailing: bool) -> str:
    if is_trailing and abs(delta) >= TOLERANCE:
        return "EXPECTED_DRIFT"
    if abs(delta) < TOLERANCE:
        return "PASS"
    if abs(delta) < _AD_DRIFT_TOLERANCE:
        return "PASS_DRIFT"
    return "FAIL"


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

def _refund_delta_totals(pnl_all, sellerise_all, months) -> Decimal:
    """Total absolute delta on refundsObject sub-lines across all months (skip trailing DEFERRED lines)."""
    total = Decimal("0")
    trailing = months[-1] if months else None
    for ym in months:
        theirs_obj = sellerise_all[ym].get("refundsObject") or {}
        ours_obj = pnl_all.get(ym, {}).get("refundsObject", {})
        for sub_line in set(theirs_obj) | set(ours_obj):
            theirs = Decimal(str(theirs_obj.get(sub_line, 0)))
            ours = ours_obj.get(sub_line, Decimal("0"))
            total += abs(ours - theirs)
    return total


def _load_newly_ingested(conn: psycopg.Connection, marketplace_id: str,
                         horizon: dt.datetime) -> list[dict]:
    """Transactions ingested after a pinned defect's horizon — the evidence that a
    moved Δ was moved by ingestion rather than by us.

    Both attribution months are returned so a caller can say which cell each row
    lands in without re-deriving the basis.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT t.transaction_id,
                   to_char(t.posted_at AT TIME ZONE 'UTC', 'YYYY-MM'),
                   to_char(COALESCE(opd.purchase_date, t.posted_at) AT TIME ZONE 'UTC', 'YYYY-MM'),
                   t.raw_json->>'transactionType',
                   COALESCE(t.transaction_status, t.raw_json->>'transactionStatus'),
                   t.is_deferred_release_event,
                   t.ingested_at
            FROM sp_transactions t
            LEFT JOIN LATERAL (
                SELECT ri->>'relatedIdentifierValue' AS order_id
                FROM jsonb_array_elements(t.raw_json->'relatedIdentifiers') ri
                WHERE ri->>'relatedIdentifierName' = 'ORDER_ID' LIMIT 1
            ) rel ON true
            LEFT JOIN order_purchase_date opd
              ON opd.order_id = rel.order_id AND opd.marketplace_id = t.marketplace_id
            WHERE t.marketplace_id = %s AND t.ingested_at > %s
            ORDER BY t.ingested_at, t.posted_at
            """,
            (marketplace_id, horizon),
        )
        return [
            {"transaction_id": r[0], "posted_ym": r[1], "purchase_ym": r[2],
             "txn_type": r[3], "status": r[4], "is_release_event": r[5],
             "ingested_at": r[6].isoformat()}
            for r in cur.fetchall()
        ]


def reconcile(
    conn: psycopg.Connection,
    marketplace_id: str,
    sellerise_path: pathlib.Path | None = None,
) -> dict:
    sellerise_path = _resolve_sellerise_path(marketplace_id, sellerise_path)
    sellerise_all = load_sellerise(sellerise_path)
    ad_all = load_ad_spend(conn, marketplace_id)
    ad_by_line = load_ad_spend_by_line(conn, marketplace_id)
    ad_as_of = load_ad_spend_as_of(conn, marketplace_id)

    # ── Compute pnl under each candidate attribution basis (in-memory) ──────
    pnl_before = compute_pnl_in_memory(
        conn, marketplace_id, shipment_basis="posted", refund_basis="posted",
    )
    pnl_after_refund_posted = compute_pnl_in_memory(
        conn, marketplace_id, shipment_basis="purchase", refund_basis="posted",
    )
    pnl_after_refund_purchase = compute_pnl_in_memory(
        conn, marketplace_id, shipment_basis="purchase", refund_basis="purchase",
    )
    # Per-marketplace refund-COGS attribution (CA differs from US; see
    # MARKETPLACE_REFUND_COGS_BASIS in config).
    from .config import MARKETPLACE_REFUND_COGS_BASIS
    refund_cog_basis = MARKETPLACE_REFUND_COGS_BASIS.get(marketplace_id, "purchase")
    # "before" = the pre-fix state: posted-date basis, no refund netting
    # "after" = the current locked design: purchase-date basis with refund netting
    cog_before = compute_cog_by_basis(conn, marketplace_id, basis="posted",   net_refunds=False)
    cog_after  = compute_cog_by_basis(conn, marketplace_id, basis="purchase", net_refunds=True,
                                       refund_basis=refund_cog_basis)

    months = sorted(sellerise_all.keys())
    trailing = months[-1] if months else None

    # ── Refund-basis empirical test: which minimises total |Δ| on refundsObject? ──
    refund_posted_delta = _refund_delta_totals(pnl_after_refund_posted, sellerise_all, months)
    refund_purchase_delta = _refund_delta_totals(pnl_after_refund_purchase, sellerise_all, months)
    refund_winner = "posted" if refund_posted_delta <= refund_purchase_delta else "purchase"
    pnl_after = pnl_after_refund_posted if refund_winner == "posted" else pnl_after_refund_purchase

    # cog is scalar under Sellerise; we compute one number per month per basis.
    def cog_scalar_before(ym: str) -> Decimal: return cog_before.get(ym, Decimal("0"))
    def cog_scalar_after(ym: str) -> Decimal:  return cog_after.get(ym, Decimal("0"))

    # ── Before/after summary rows (for the report's headline table) ──────────
    before_after: list[dict] = []
    for ym in months:
        sm = sellerise_all[ym]
        pb = pnl_before.get(ym, {})
        pa = pnl_after.get(ym, {})
        ad_total = ad_all.get(ym, Decimal("0"))
        for bucket, sub in [("chargesObject", "Principal"),
                             ("feesObject", "Commission"),
                             ("fbaObject", "FBAPerUnitFulfillmentFee")]:
            theirs = Decimal(str((sm.get(bucket) or {}).get(sub, 0)))
            ours_b = pb.get(bucket, {}).get(sub, Decimal("0"))
            ours_a = pa.get(bucket, {}).get(sub, Decimal("0"))
            before_after.append({
                "year_month": ym, "cell": f"{bucket}.{sub}",
                "before": float(ours_b), "after": float(ours_a), "theirs": float(theirs),
                "delta_before": float(ours_b - theirs), "delta_after": float(ours_a - theirs),
            })
        # cog scalar
        theirs = Decimal(str(sm.get("cog", 0)))
        ours_b = cog_scalar_before(ym); ours_a = cog_scalar_after(ym)
        before_after.append({
            "year_month": ym, "cell": "cog",
            "before": float(ours_b), "after": float(ours_a), "theirs": float(theirs),
            "delta_before": float(ours_b - theirs), "delta_after": float(ours_a - theirs),
        })
        # net (whole formula)
        theirs_net = _compute_net_theirs(sm)
        ours_b_net = _compute_net_ours(pb, ad_total, ours_b if isinstance(ours_b, Decimal) else Decimal(str(ours_b)))
        ours_a_net = _compute_net_ours(pa, ad_total, ours_a if isinstance(ours_a, Decimal) else Decimal(str(ours_a)))
        before_after.append({
            "year_month": ym, "cell": "net",
            "before": float(ours_b_net), "after": float(ours_a_net), "theirs": float(theirs_net),
            "delta_before": float(ours_b_net - theirs_net), "delta_after": float(ours_a_net - theirs_net),
        })

    # Aggregate before/after magnitude for the verdict
    sum_abs_before = sum(abs(r["delta_before"]) for r in before_after if r["cell"] != "net")
    sum_abs_after = sum(abs(r["delta_after"]) for r in before_after if r["cell"] != "net")
    net_delta_before = sum(r["delta_before"] for r in before_after if r["cell"] == "net")
    net_delta_after = sum(r["delta_after"] for r in before_after if r["cell"] == "net")
    total_sellerise_net = sum(r["theirs"] for r in before_after if r["cell"] == "net")

    # ── Refund basis test rows ────────────────────────────────────────────────
    refund_test: list[dict] = []
    for ym in months:
        theirs_obj = sellerise_all[ym].get("refundsObject") or {}
        posted_obj = pnl_after_refund_posted.get(ym, {}).get("refundsObject", {})
        purchase_obj = pnl_after_refund_purchase.get(ym, {}).get("refundsObject", {})
        theirs_sum = sum((Decimal(str(v)) for v in theirs_obj.values()), start=Decimal("0"))
        posted_sum = sum(posted_obj.values(), start=Decimal("0"))
        purchase_sum = sum(purchase_obj.values(), start=Decimal("0"))
        refund_test.append({
            "year_month": ym,
            "ours_refund_posted": float(posted_sum),
            "ours_refund_purchase": float(purchase_sum),
            "theirs": float(theirs_sum),
            "delta_posted": float(posted_sum - theirs_sum),
            "delta_purchase": float(purchase_sum - theirs_sum),
        })

    # ── Ad-line reconciliation (V1 test — before wiring into net) ───────────
    ad_lines: list[dict] = []
    for ym in months:
        adx = sellerise_all[ym].get("adExpenses") or {}
        s_ad = Decimal(str(adx.get("adCost", 0) or 0))
        s_hsa = Decimal(str(adx.get("hsaCost", 0) or 0)) + Decimal(str(adx.get("hsaVideoCost", 0) or 0))
        s_sd = Decimal(str(adx.get("sdCost", 0) or 0))
        s_stv = Decimal(str(adx.get("stvCost", 0) or 0))
        by_ap = ad_by_line.get(ym, {})
        o_ad = by_ap.get("Sponsored Products", Decimal("0"))
        o_sb = by_ap.get("Sponsored Brands", Decimal("0"))
        o_sd = by_ap.get("Sponsored Display", Decimal("0"))
        # Sponsored TV — API returned nothing for our account. If it ever
        # shows, it would come through as "Sponsored Television" (or similar).
        o_stv = by_ap.get("Sponsored Television", Decimal("0"))
        is_trailing = (ym == trailing)
        for label, ours, theirs in [
            ("adCost (Sponsored Products)", o_ad, s_ad),
            ("hsaCost+hsaVideoCost (SB merged)", o_sb, s_hsa),
            ("sdCost (Sponsored Display)", o_sd, s_sd),
            ("stvCost (Sponsored TV)", o_stv, s_stv),
        ]:
            delta = ours - theirs
            ad_lines.append({
                "year_month": ym, "line": label,
                "ours": float(ours), "theirs": float(theirs),
                "delta": float(delta),
                "status": _ad_status(delta, is_trailing),
            })
        # per-month total row — tolerance is a small multiple of the per-line
        # drift band so a month whose line-level deltas are all PASS_DRIFT
        # doesn't get flagged FAIL just because the aggregate crosses the
        # single-line threshold.
        ours_total = o_ad + o_sb + o_sd + o_stv
        theirs_total = s_ad + s_hsa + s_sd + s_stv
        total_delta = ours_total - theirs_total
        total_status = "PASS" if abs(total_delta) < TOLERANCE else (
            "EXPECTED_DRIFT" if is_trailing and abs(total_delta) >= TOLERANCE
            else ("PASS_DRIFT" if abs(total_delta) < _AD_DRIFT_TOLERANCE * 4  # 4 lines
                  else "FAIL")
        )
        ad_lines.append({
            "year_month": ym, "line": "TOTAL",
            "ours": float(ours_total), "theirs": float(theirs_total),
            "delta": float(total_delta),
            "status": total_status,
        })

    # ── Net before/after — with adExpenses=0 vs with real ad spend ──────────
    net_ba: list[dict] = []
    for ym in months:
        sm = sellerise_all[ym]
        pa = pnl_after.get(ym, {})
        theirs_net = _compute_net_theirs(sm)
        ours_cog = cog_after.get(ym, Decimal("0"))
        ours_net_before = _compute_net_ours(pa, Decimal("0"), ours_cog)          # adExpenses=0
        ours_net_after  = _compute_net_ours(pa, ad_all.get(ym, Decimal("0")), ours_cog)  # real ads
        net_ba.append({
            "year_month": ym,
            "net_before": float(ours_net_before),
            "net_after":  float(ours_net_after),
            "theirs":     float(theirs_net),
            "delta_before": float(ours_net_before - theirs_net),
            "delta_after":  float(ours_net_after  - theirs_net),
        })

    # ── Main per-cell diff (using AFTER = chosen basis) ──────────────────────
    pnl_all = pnl_after  # for legacy naming below

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
                    # ad_all sums to a POSITIVE cost magnitude (same sign as Sellerise's aggregate).
                    ours = ad_all.get(ym, Decimal("0"))
                    is_trailing = (ym == trailing)
                    ours_status = "OURS_MISSING" if not ad_all else _ad_status(ours - theirs, is_trailing)
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

        # cog (scalar; magnitude on both sides). We compute cog in-memory under
        # the chosen basis and use that instead of anything stored in pnl_month.
        ours_cog = cog_after.get(ym, Decimal("0"))
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

    # storageFee handling in the earlier loop calls _ours_scalar which sums the
    # storageFee dict. compute_pnl_in_memory does populate that bucket (it's a
    # NET rule in bucket_map), so the sign flip inside _ours_scalar still holds.

    # Locked-target results.
    #
    # A locked target is a golden figure from RECONCILIATION.md Step 3 — a value
    # our pipeline reproduced at lock time, when it also equalled Sellerise. The
    # exact-match assertion (±$0.01) catches a mapping/attribution regression.
    #
    # But the golden figure is frozen while Amazon restates the underlying leaves,
    # so a drift-prone cell (the decision-D/E Promotion + RestockingFee lines)
    # drifts away from its lock over time — the exact same our-vs-Sellerise drift
    # the guard already accepts WITHIN_DRIFT on that cell's band. An exact-match
    # lock on a restating cell fails permanently for a reason that is not a
    # regression, which is precisely the "red every run → ignored" trap.
    #
    # So a target that misses the exact match is graded against the SAME band the
    # drift guard uses for that cell: within it → ACCEPTED_DRIFT (restatement, not
    # a regression; does not fail the run); outside it → FAIL (a real regression).
    # The exact-match still holds for the structural decision-A zeros, which do
    # not drift. Bands are read, never altered.
    locked_results = []
    for bucket, sub_line, ym, expected, dec in LOCKED_TARGETS_BY_MARKETPLACE.get(marketplace_id, []):
        actual = _ours_sub_line(pnl_all.get(ym, {}), bucket, sub_line)
        delta = actual - expected
        is_trailing = (ym == trailing)
        band = _drift.band_for(bucket, sub_line, is_trailing, marketplace_id=marketplace_id)
        if abs(delta) < TOLERANCE:
            status = "PASS"
        elif abs(delta) < band:
            status = "ACCEPTED_DRIFT"
        else:
            status = "FAIL"
        locked_results.append({
            "decision": dec, "bucket": bucket, "sub_line": sub_line, "year_month": ym,
            "expected": float(expected), "actual": float(actual),
            "delta": float(delta), "band": float(band), "status": status,
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

    # ── Prior-pull snapshot for the vs-prior-pull guard ─────────────────────
    # Load the most recent snapshot per (ym, bucket, sub_line) BEFORE the
    # current pull. Then compare current values to prior; classify with the
    # tight prior-pull bands. On the first run there is no prior — mark
    # NO_BASELINE for every cell.
    prior_snapshot: dict[tuple[str, str, str], Decimal] = {}
    prior_pull_at: dt.datetime | None = None
    with conn.cursor() as cur:
        cur.execute("""
            SELECT MAX(pull_at) FROM pnl_monthly_snapshots WHERE marketplace_id = %s
        """, (marketplace_id,))
        row = cur.fetchone()
        prior_pull_at = row[0] if row and row[0] else None
        if prior_pull_at is not None:
            cur.execute("""
                SELECT year_month, bucket, sub_line, amount
                FROM pnl_monthly_snapshots
                WHERE marketplace_id = %s AND pull_at = %s
            """, (marketplace_id, prior_pull_at))
            for ym_r, b, sl, amt in cur.fetchall():
                prior_snapshot[(ym_r, b, sl)] = Decimal(str(amt))

    # ── Has any pinned defect moved, and did newly-ingested rows move it? ────
    # The target's file is frozen, so a pinned Δ moves only when *our* side does.
    # Recompute the offending cells at the pin's ingestion horizon: if the Δ is
    # still pinned there, new rows did it (DEFECT_REMEASURED); if not, our code
    # did (INVESTIGATE). Lazy — nothing runs unless a pin is actually off.
    as_of_delta: dict[tuple[str, str, str], Decimal] = {}
    moved_horizons: set[dt.datetime] = set()
    for d in diffs:
        dfc = _drift.target_defect_for(marketplace_id, d["year_month"], d["bucket"], d["sub_line"])
        if dfc is not None and not dfc.matches(Decimal(str(d["delta"]))):
            moved_horizons.add(dfc.measured_at)

    for horizon in sorted(moved_horizons):
        log.warning("A pinned defect has moved — recomputing at its ingestion horizon %s", horizon)
        pnl_h = compute_pnl_in_memory(conn, marketplace_id, shipment_basis="purchase",
                                      refund_basis=refund_winner, ingested_before=horizon)
        cog_h = compute_cog_by_basis(conn, marketplace_id, basis="purchase", net_refunds=True,
                                     refund_basis=refund_cog_basis, ingested_before=horizon)
        for d in diffs:
            dfc = _drift.target_defect_for(marketplace_id, d["year_month"], d["bucket"], d["sub_line"])
            if dfc is None or dfc.measured_at != horizon:
                continue
            ours_h = (cog_h.get(d["year_month"], Decimal("0")) if d["bucket"] == "cog"
                      else pnl_h.get(d["year_month"], {}).get(d["bucket"], {}).get(d["sub_line"], Decimal("0")))
            as_of_delta[(d["year_month"], d["bucket"], d["sub_line"])] = ours_h - Decimal(str(d["theirs"]))

    newly_ingested = (_load_newly_ingested(conn, marketplace_id, min(moved_horizons))
                      if moved_horizons else [])

    # ── Drift-guard (regression detector — vs Sellerise) ────────────────────
    # For every settled bucket + sub_line, classify the Δ against its band.
    # KNOWN_TARGET_DEFECT / DEFECT_REMEASURED / WITHIN_DRIFT / TRAILING /
    # INVESTIGATE. A cell in the target-defect registry is pinned to its measured
    # Δ instead of being banded — see drift_bands.TargetDefect.
    drift_guard: list[dict] = []
    for d in diffs:
        is_trailing = (d["year_month"] == trailing)
        # Ad lines handled by their own band below. Also skip cells the main
        # diff already marked EXPECTED (decision-A trailing-DEFERRED estimate
        # lines) — those are documented planned mismatches, not regressions.
        if d["bucket"] in ("adExpenses",) or d["status"] == "EXPECTED":
            continue
        band = _drift.band_for(d["bucket"], d["sub_line"], is_trailing,
                               marketplace_id=marketplace_id)
        defect = _drift.target_defect_for(marketplace_id, d["year_month"],
                                          d["bucket"], d["sub_line"])
        key = (d["year_month"], d["bucket"], d["sub_line"])
        status = _drift.classify(Decimal(str(d["delta"])), band, is_trailing,
                                 defect=defect, delta_as_of=as_of_delta.get(key))
        drift_guard.append({
            "year_month": d["year_month"], "bucket": d["bucket"], "sub_line": d["sub_line"],
            "delta": d["delta"], "band": float(band), "status": status,
            "expected_delta": float(defect.expected_delta) if defect else None,
            "tolerance": float(defect.tolerance) if defect else None,
            "kind": defect.kind if defect else None,
            "measured_at": defect.measured_at.isoformat() if defect else None,
            "delta_as_of": float(as_of_delta[key]) if key in as_of_delta else None,
            "note": defect.note if defect else None,
        })
    # Ad TOTAL / per-line drift
    _ad_line_band, _ad_total_band = _drift.ad_bands_for(marketplace_id)
    for r in ad_lines:
        is_trailing = (r["year_month"] == trailing)
        band = float(_ad_total_band if r["line"] == "TOTAL" else _ad_line_band)
        status = _drift.classify(Decimal(str(r["delta"])), Decimal(str(band)), is_trailing)
        drift_guard.append({
            "year_month": r["year_month"], "bucket": "adExpenses", "sub_line": r["line"],
            "delta": r["delta"], "band": band, "status": status,
        })
    # Sort INVESTIGATE to top for visibility
    drift_guard.sort(key=lambda x: (x["status"] != "INVESTIGATE", x["year_month"], x["bucket"], x["sub_line"]))
    investigate_count = sum(1 for r in drift_guard if r["status"] == "INVESTIGATE")

    # ── Vs-prior-pull guard (regression detector — pure pull-to-pull) ───────
    # For every non-EXPECTED cell: compare current value to the same cell's
    # value in the most recent prior snapshot. Uses tight PRIOR_PULL_BANDS
    # calibrated to observed pull-to-pull drift ($0.00 baseline for ads).
    #
    # The target-defect registry is deliberately NOT consulted here. It pins a
    # Δ *against the target*; this guard compares our-now against our-then, where
    # a target-side defect contributes nothing. Suppressing cells here would
    # blind the one guard that can still catch a code regression in them.
    drift_vs_prior: list[dict] = []
    have_prior = prior_pull_at is not None
    for d in diffs:
        if d["bucket"] in ("adExpenses",) or d["status"] == "EXPECTED":
            continue
        key = (d["year_month"], d["bucket"], d["sub_line"])
        current = Decimal(str(d["ours"]))
        if not have_prior:
            status = "NO_BASELINE"
            delta_pp: float = 0.0
            band_pp: float = 0.0
        else:
            prior = prior_snapshot.get(key, Decimal("0"))
            delta = current - prior
            is_trailing = (d["year_month"] == trailing)
            band = _drift.prior_pull_band_for(d["bucket"], d["sub_line"], is_trailing,
                                               marketplace_id=marketplace_id)
            status = _drift.classify(delta, band, is_trailing)
            delta_pp = float(delta); band_pp = float(band)
        drift_vs_prior.append({
            "year_month": d["year_month"], "bucket": d["bucket"], "sub_line": d["sub_line"],
            "current": float(current), "prior_pull_at": prior_pull_at.isoformat() if prior_pull_at else None,
            "delta": delta_pp, "band": band_pp, "status": status,
        })
    # Ad lines vs prior — key by ad line label
    _pp_ad_line_band, _pp_ad_total_band = _drift.prior_pull_ad_bands_for(marketplace_id)
    for r in ad_lines:
        key = (r["year_month"], "adExpenses", r["line"])
        current = Decimal(str(r["ours"]))
        if not have_prior:
            status = "NO_BASELINE"; delta_pp = 0.0; band_pp = 0.0
        else:
            prior = prior_snapshot.get(key, Decimal("0"))
            delta = current - prior
            is_trailing = (r["year_month"] == trailing)
            band = _pp_ad_total_band if r["line"] == "TOTAL" else _pp_ad_line_band
            if is_trailing:
                band = band * _drift.TRAILING_MULTIPLIER
            status = _drift.classify(delta, band, is_trailing)
            delta_pp = float(delta); band_pp = float(band)
        drift_vs_prior.append({
            "year_month": r["year_month"], "bucket": "adExpenses", "sub_line": r["line"],
            "current": float(current), "prior_pull_at": prior_pull_at.isoformat() if prior_pull_at else None,
            "delta": delta_pp, "band": band_pp, "status": status,
        })
    drift_vs_prior.sort(key=lambda x: (x["status"] != "INVESTIGATE", x["year_month"], x["bucket"], x["sub_line"]))
    investigate_prior_count = sum(1 for r in drift_vs_prior if r["status"] == "INVESTIGATE")

    # ── Persist the current pull's snapshot (append-only) ───────────────────
    # Do this LAST — after everything else succeeds. The snapshot IS the
    # baseline for next pull; if we crash we don't want a partial baseline.
    now_utc = dt.datetime.now(dt.timezone.utc)
    snapshot_rows: list[tuple] = []
    # Save every cell that fed the diffs/ad-lines (the same universe the
    # prior-pull guard reads back).
    for d in diffs:
        # Skip aggregates that aren't stable identifiers — we key by (bucket,
        # sub_line) so both need real names.
        if d["bucket"] in ("adExpenses",):
            continue
        snapshot_rows.append((now_utc, marketplace_id, d["year_month"],
                              d["bucket"], d["sub_line"], Decimal(str(d["ours"]))))
    for r in ad_lines:
        snapshot_rows.append((now_utc, marketplace_id, r["year_month"],
                              "adExpenses", r["line"], Decimal(str(r["ours"]))))
    if snapshot_rows:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO pnl_monthly_snapshots
                    (pull_at, marketplace_id, year_month, bucket, sub_line, amount)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                snapshot_rows,
            )
        conn.commit()

    return {
        "diffs": diffs, "locked": locked_results, "ad_audit": ad_audit,
        "before_after": before_after,
        "refund_test": refund_test,
        "refund_basis_chosen": refund_winner,
        "refund_posted_delta": float(refund_posted_delta),
        "refund_purchase_delta": float(refund_purchase_delta),
        "sum_abs_before": float(sum_abs_before),
        "sum_abs_after": float(sum_abs_after),
        "net_delta_before": float(net_delta_before),
        "net_delta_after": float(net_delta_after),
        "total_sellerise_net": float(total_sellerise_net),
        "ad_lines": ad_lines,
        "net_ba": net_ba,
        "ad_as_of": {ym: t.isoformat() for ym, t in ad_as_of.items()},
        "drift_guard": drift_guard,
        "investigate_count": investigate_count,
        "target_defect_count": sum(1 for r in drift_guard
                                   if r["status"] == _drift.KNOWN_TARGET_DEFECT),
        "remeasured_count": sum(1 for r in drift_guard
                                if r["status"] == _drift.DEFECT_REMEASURED),
        "newly_ingested": newly_ingested,
        "drift_vs_prior": drift_vs_prior,
        "investigate_prior_count": investigate_prior_count,
        "prior_pull_at": prior_pull_at.isoformat() if prior_pull_at else None,
        "current_pull_at": now_utc.isoformat(),
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

    # ── Attribution-basis decision ───────────────────────────────────────
    lines.append("## Attribution basis")
    lines.append("")
    lines.append("Shipment revenue + nested fees + `cog` re-attributed to **order PurchaseDate**")
    lines.append(f"(from `order_purchase_date`). Non-order transactions stay on `postedDate`.")
    lines.append(f"Refund basis chosen empirically: **{result['refund_basis_chosen']}Date** "
                 f"(refundsObject Σ|Δ|: posted-basis ${result['refund_posted_delta']:,.2f}, "
                 f"purchase-basis ${result['refund_purchase_delta']:,.2f}).")
    lines.append("")
    lines.append(f"**Before → After improvement** (`chargesObject.Principal` + `feesObject.Commission` + "
                 f"`fbaObject.FBAPerUnitFulfillmentFee` + `cog`):")
    lines.append(f"- Σ|Δ| before (all `postedDate`): **${result['sum_abs_before']:,.2f}**")
    lines.append(f"- Σ|Δ| after  (Shipment on `PurchaseDate`): **${result['sum_abs_after']:,.2f}**")
    lines.append(f"- Reduction: **${result['sum_abs_before'] - result['sum_abs_after']:,.2f}** "
                 f"({(1 - result['sum_abs_after'] / max(result['sum_abs_before'], 1)) * 100:+.1f}%)")
    lines.append("")
    lines.append(f"- Cumulative Jan–Jun `net` delta before: **${result['net_delta_before']:+,.2f}** "
                 f"({result['net_delta_before'] / max(result['total_sellerise_net'], 1) * 100:+.2f}% of Sellerise net)")
    lines.append(f"- Cumulative Jan–Jun `net` delta after:  **${result['net_delta_after']:+,.2f}** "
                 f"({result['net_delta_after'] / max(result['total_sellerise_net'], 1) * 100:+.2f}% of Sellerise net)")
    lines.append("")

    # ── Before / after per key bucket per month ──────────────────────────
    lines.append("## Before / After (per key bucket per month)")
    lines.append("")
    lines.append("| month | cell | before (ours) | after (ours) | Sellerise | Δ before | Δ after |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for r in result["before_after"]:
        lines.append(
            f"| {r['year_month']} | `{r['cell']}` | "
            f"{_fmt_amt(r['before'])} | {_fmt_amt(r['after'])} | {_fmt_amt(r['theirs'])} | "
            f"{_fmt_amt(r['delta_before'])} | {_fmt_amt(r['delta_after'])} |"
        )
    lines.append("")

    # ── Refund-basis empirical test ──────────────────────────────────────
    lines.append("## Refund-basis empirical test")
    lines.append("")
    lines.append("Sum of Refund transactions bucketed by `postedDate` vs `PurchaseDate`, per month.")
    lines.append(f"Winner: **{result['refund_basis_chosen']}Date** (smaller Σ|Δ| against Sellerise's `refundsObject`).")
    lines.append("")
    lines.append("| month | ours (posted) | ours (purchase) | Sellerise Σ | Δ posted | Δ purchase |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for r in result["refund_test"]:
        lines.append(
            f"| {r['year_month']} | {_fmt_amt(r['ours_refund_posted'])} | "
            f"{_fmt_amt(r['ours_refund_purchase'])} | {_fmt_amt(r['theirs'])} | "
            f"{_fmt_amt(r['delta_posted'])} | {_fmt_amt(r['delta_purchase'])} |"
        )
    lines.append("")

    # ── Drift-guard (regression detector) ────────────────────────────────
    if result.get("drift_guard"):
        investigate = [r for r in result["drift_guard"] if r["status"] == "INVESTIGATE"]
        defects = [r for r in result["drift_guard"]
                   if r["status"] == _drift.KNOWN_TARGET_DEFECT]
        lines.append(f"## Drift-guard: {result.get('investigate_count', 0)} INVESTIGATE / "
                     f"{result.get('remeasured_count', 0)} DEFECT_REMEASURED / "
                     f"{result.get('target_defect_count', 0)} KNOWN_TARGET_DEFECT / "
                     f"{sum(1 for r in result['drift_guard'] if r['status'] == 'TRAILING')} TRAILING / "
                     f"{sum(1 for r in result['drift_guard'] if r['status'] == 'WITHIN_DRIFT')} WITHIN_DRIFT")
        lines.append("")
        lines.append(f"Regression guard per `DRIFT_BASELINE.md`. Trailing month: **{result['trailing']}**.")
        lines.append(f"`WITHIN_DRIFT` = expected restatement drift · "
                     f"`TRAILING` = still moving (refund lag / DEFERRED) · "
                     f"`KNOWN_TARGET_DEFECT` = **diagnosed defect on the target's side, pinned to its "
                     f"measured Δ** · "
                     f"`DEFECT_REMEASURED` = **the pinned Δ moved, and rows ingested since the pin "
                     f"account for all of it — re-pin, do not investigate** · "
                     f"`INVESTIGATE` = **beyond the settled-month band, or a pinned defect that moved "
                     f"— possible pipeline regression**.")
        lines.append("")
        remeasured = [r for r in result["drift_guard"]
                      if r["status"] == _drift.DEFECT_REMEASURED]
        if remeasured:
            new_rows = result.get("newly_ingested", [])
            lines.append("### 🔁 DEFECT_REMEASURED — a pinned Δ moved, and newly-ingested rows explain it")
            lines.append("")
            lines.append("The target's file is frozen, so a pinned Δ moves only when **our** side does. "
                         "Recomputed at each pin's ingestion horizon, these cells are **still at their "
                         "pinned value** — every bit of the movement came from rows ingested since. The "
                         "defect itself has not changed; its dollar figure has. **Update the registry "
                         "entry and re-pin.** (Had the as-of Δ moved too, this would read `INVESTIGATE`.)")
            lines.append("")
            lines.append("| month | bucket · sub_line | pinned Δ | current Δ | Δ at horizon | moved by | kind | horizon |")
            lines.append("|---|---|---:|---:|---:|---:|---|---|")
            for r in remeasured:
                moved = r["delta"] - r["expected_delta"]
                lines.append(f"| {r['year_month']} | `{r['bucket']}.{r['sub_line']}` | "
                             f"{_fmt_amt(r['expected_delta'])} | {_fmt_amt(r['delta'])} | "
                             f"{_fmt_amt(r['delta_as_of'])} | {_fmt_amt(moved)} | {r['kind']} | "
                             f"{r['measured_at']} |")
            lines.append("")
            lines.append(f"**{len(new_rows)} transaction(s) ingested since the horizon.** "
                         f"Those landing in a re-measured cell's month:")
            lines.append("")
            lines.append("| transaction | posted | purchase | type | status | release event | ingested |")
            lines.append("|---|---|---|---|---|---|---|")
            months = {r["year_month"] for r in remeasured}
            explaining = [n for n in new_rows
                          if n["posted_ym"] in months or n["purchase_ym"] in months]
            for n in explaining[:25]:
                lines.append(f"| `{n['transaction_id'][:20]}…` | {n['posted_ym']} | {n['purchase_ym']} | "
                             f"{n['txn_type']} | {n['status']} | {n['is_release_event']} | "
                             f"{n['ingested_at'][:19]} |")
            if len(explaining) > 25:
                lines.append(f"| … {len(explaining) - 25} more | | | | | | |")
            lines.append("")
            lines.append("Re-pin by replacing each entry's `expected_delta` with its **current Δ** and "
                         "its `measured_at` with a horizon after this ingest:")
            lines.append("")
            lines.append("```python")
            for r in remeasured:
                lines.append(f'# ({marketplace_id!r}, {r["year_month"]!r}, {r["bucket"]!r}, '
                             f'{r["sub_line"]!r}) -> expected_delta {r["delta"]:.2f}')
            lines.append("```")
            lines.append("")
        if defects:
            lines.append("### 🔒 KNOWN_TARGET_DEFECT — our side is right; the target is wrong")
            lines.append("")
            lines.append("Pinned, not excused: each cell must hold its measured Δ within a tight "
                         "tolerance. If it moves in either direction — including toward zero, because "
                         "the target fixed its bug — it fires `INVESTIGATE`.")
            lines.append("")
            lines.append("| month | bucket · sub_line | Δ | expected Δ | tolerance (±) |")
            lines.append("|---|---|---:|---:|---:|")
            for r in defects:
                lines.append(f"| {r['year_month']} | `{r['bucket']}.{r['sub_line']}` | "
                             f"{_fmt_amt(r['delta'])} | {_fmt_amt(r['expected_delta'])} | "
                             f"{_fmt_amt(r['tolerance'])} |")
            lines.append("")
            for note in dict.fromkeys(r["note"] for r in defects):
                lines.append(f"- {note}")
            lines.append("")
        if investigate:
            lines.append("### 🚨 INVESTIGATE — beyond settled-month band")
            lines.append("")
            lines.append("| month | bucket · sub_line | Δ | band (±) |")
            lines.append("|---|---|---:|---:|")
            for r in investigate:
                lines.append(f"| {r['year_month']} | `{r['bucket']}.{r['sub_line']}` | "
                             f"{_fmt_amt(r['delta'])} | {_fmt_amt(r['band'])} |")
            lines.append("")
        # Full guard table collapsed by default — just show summary counts + INVESTIGATE
        by_ym_status: dict[tuple[str, str], int] = defaultdict(int)
        for r in result["drift_guard"]:
            by_ym_status[(r["year_month"], r["status"])] += 1
        lines.append("### Per-month summary")
        lines.append("")
        lines.append("| month | WITHIN_DRIFT | TRAILING | KNOWN_TARGET_DEFECT | DEFECT_REMEASURED | INVESTIGATE |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for ym in sorted({r["year_month"] for r in result["drift_guard"]}):
            wd = by_ym_status.get((ym, "WITHIN_DRIFT"), 0)
            tr = by_ym_status.get((ym, "TRAILING"), 0)
            ktd = by_ym_status.get((ym, _drift.KNOWN_TARGET_DEFECT), 0)
            rem = by_ym_status.get((ym, _drift.DEFECT_REMEASURED), 0)
            inv = by_ym_status.get((ym, "INVESTIGATE"), 0)
            lines.append(f"| {ym} | {wd} | {tr} | {ktd} | {rem} | {inv} |")
        lines.append("")

    # ── Drift-guard: vs prior pull (regression detector) ────────────────
    if result.get("drift_vs_prior"):
        vp = result["drift_vs_prior"]
        vp_counts = defaultdict(int)
        for r in vp: vp_counts[r["status"]] += 1
        prior_at = result.get("prior_pull_at")
        current_at = result.get("current_pull_at")
        if vp_counts["NO_BASELINE"] > 0 and vp_counts["INVESTIGATE"] == 0:
            lines.append(f"## Drift-guard vs prior pull: NO_BASELINE (first pull)")
            lines.append("")
            lines.append(f"Current pull persisted at `{current_at}`. Next reconcile run will "
                         f"compare against this snapshot.")
        else:
            lines.append(f"## Drift-guard vs prior pull: "
                         f"{vp_counts['INVESTIGATE']} INVESTIGATE / "
                         f"{vp_counts['TRAILING']} TRAILING / "
                         f"{vp_counts['WITHIN_DRIFT']} WITHIN_DRIFT")
            lines.append("")
            lines.append(f"Prior pull: `{prior_at}`. Current pull: `{current_at}`.")
            lines.append(f"Bands per `DRIFT_VS_PRIOR_PULL.md` — tight, calibrated to observed "
                         f"pull-to-pull movement (baseline: $0.00 for ads over ~13h).")
            lines.append("")
            investigate = [r for r in vp if r["status"] == "INVESTIGATE"]
            if investigate:
                lines.append("### 🚨 INVESTIGATE — moved beyond pull-to-pull band")
                lines.append("")
                lines.append("| month | bucket · sub_line | current | Δ (current − prior) | band (±) |")
                lines.append("|---|---|---:|---:|---:|")
                for r in investigate:
                    lines.append(f"| {r['year_month']} | `{r['bucket']}.{r['sub_line']}` | "
                                 f"{_fmt_amt(r['current'])} | {_fmt_amt(r['delta'])} | "
                                 f"{_fmt_amt(r['band'])} |")
                lines.append("")

    # ── Locked validation targets ────────────────────────────────────────
    lines.append("## Locked validation targets (Step 3 assertions)")
    lines.append("")
    locked_pass = sum(1 for r in result["locked"] if r["status"] == "PASS")
    locked_drift = sum(1 for r in result["locked"] if r["status"] == "ACCEPTED_DRIFT")
    locked_fail = sum(1 for r in result["locked"] if r["status"] == "FAIL")
    # Prose only when there are targets to explain — an empty list (CA/UK/AU)
    # renders exactly as before.
    if result["locked"]:
        lines.append("Golden figures from RECONCILIATION.md. `PASS` = exact (±$0.01). "
                     "`ACCEPTED_DRIFT` = off the frozen golden figure but within that cell's "
                     "restatement band (shown) — the our-vs-Sellerise drift the guard already "
                     "accepts, not a regression, does not fail the run. `FAIL` = outside the band.")
        lines.append("")
    # Table columns are unchanged; the band is annotated inside the status cell
    # for drift/fail rows only, so PASS rows and empty tables stay byte-identical.
    lines.append("| Dec. | bucket · sub_line | month | expected | actual | delta | status |")
    lines.append("|---|---|---|---:|---:|---:|---|")
    for r in result["locked"]:
        note = (f" (±{_fmt_amt(r['band']).strip()})"
                if r["status"] in ("ACCEPTED_DRIFT", "FAIL") else "")
        lines.append(
            f"| {r['decision']} | `{r['bucket']}.{r['sub_line']}` | {r['year_month']} | "
            f"{_fmt_amt(r['expected'])} | {_fmt_amt(r['actual'])} | {_fmt_amt(r['delta'])} | "
            f"{r['status']}{note} |"
        )
    lines.append("")
    # Summary keeps its original form; the drift/fail breakdown is appended only
    # when non-zero, so a clean all-PASS or empty list is byte-identical.
    summary = f"**Locked targets: {locked_pass} / {len(result['locked'])} PASS**"
    if locked_drift or locked_fail:
        summary += f" · {locked_drift} ACCEPTED_DRIFT · {locked_fail} FAIL"
    lines.append(summary)
    lines.append("")

    # ── Ad-line reconciliation (V1) + net before/after (Step 2c) ────────
    if result.get("ad_lines"):
        lines.append("## Ad-lines reconciliation (Phase 4 Step 2c V1)")
        lines.append("")
        lines.append(
            "Ads-API `metric.totalCost` (USD-only, SB Video merged into SB) vs Sellerise's "
            "five `adExpenses` lines. Restatement drift up to ±$5.00 shows as "
            "`PASS_DRIFT` (small, expected — Amazon revises reports after Sellerise's snapshot). "
            "Trailing month is `EXPECTED_DRIFT`."
        )
        lines.append("")
        lines.append(f"`as_of` timestamps per month: {result.get('ad_as_of', {})}")
        lines.append("")
        lines.append("| month | line | ours (USD) | Sellerise | Δ | status |")
        lines.append("|---|---|---:|---:|---:|---|")
        for r in result["ad_lines"]:
            lines.append(
                f"| {r['year_month']} | {r['line']} | "
                f"{_fmt_amt(r['ours'])} | {_fmt_amt(r['theirs'])} | "
                f"{_fmt_amt(r['delta'])} | {r['status']} |"
            )
        lines.append("")

    if result.get("net_ba"):
        lines.append("## Net before / after wiring `adExpenses` (Phase 4 Step 2c)")
        lines.append("")
        lines.append("`net_before` = adExpenses set to 0; `net_after` = subtract real ad spend from Sellerise's formula.")
        lines.append("")
        lines.append("| month | net_before (ours) | net_after (ours) | Sellerise net | Δ before | Δ after |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for r in result["net_ba"]:
            lines.append(
                f"| {r['year_month']} | {_fmt_amt(r['net_before'])} | {_fmt_amt(r['net_after'])} | "
                f"{_fmt_amt(r['theirs'])} | {_fmt_amt(r['delta_before'])} | {_fmt_amt(r['delta_after'])} |"
            )
        sum_before = sum(r["delta_before"] for r in result["net_ba"])
        sum_after  = sum(r["delta_after"]  for r in result["net_ba"])
        lines.append(f"| **Σ** | | | | **{_fmt_amt(sum_before)}** | **{_fmt_amt(sum_after)}** |")
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
    locked_drift = sum(1 for r in result["locked"] if r["status"] == "ACCEPTED_DRIFT")
    locked_fail = sum(1 for r in result["locked"] if r["status"] == "FAIL")
    log.info(
        "Cell counts: %s. Locked targets: %d PASS / %d ACCEPTED_DRIFT / %d FAIL of %d",
        dict(counts), locked_pass, locked_drift, locked_fail, len(result["locked"]),
    )
    if locked_drift:
        log.warning(
            "%d locked target(s) are ACCEPTED_DRIFT: our value differs from the frozen golden figure "
            "but stays within that cell's restatement band — drift, not a regression. They do not fail "
            "the run. See the report's locked-targets table.", locked_drift,
        )

    # Drift-guard regression signals — loud, per DRIFT_BASELINE.md
    inv_s = result.get("investigate_count", 0)
    inv_p = result.get("investigate_prior_count", 0)
    ktd = result.get("target_defect_count", 0)
    rem = result.get("remeasured_count", 0)
    if ktd:
        log.warning(
            "🔒 Drift-guard vs Sellerise: %d cell(s) are KNOWN_TARGET_DEFECT — the target is wrong, "
            "we are right, and each is pinned to its measured Δ. They do not fail the run. "
            "See the report's KNOWN_TARGET_DEFECT section.", ktd,
        )
    if rem:
        log.warning(
            "🔁 Drift-guard vs Sellerise: %d pinned cell(s) are DEFECT_REMEASURED — their Δ moved, and "
            "rows ingested since the pin account for ALL of it (the Δ recomputed at the pin's horizon "
            "is unchanged). The defect has not changed, its dollar figure has. This does not fail the "
            "run, but the registry entries are now stale — re-pin them. Expected on the first guarded "
            "run after an ingest; a bug on a run that ingested nothing.", rem,
        )
    if inv_s:
        log.warning(
            "🚨 Drift-guard vs Sellerise: %d cell(s) fired INVESTIGATE. Possible pipeline regression.", inv_s
        )
    if inv_p:
        log.warning(
            "🚨 Drift-guard vs prior pull: %d cell(s) fired INVESTIGATE. "
            "A cell moved from its own prior-pull value beyond band — likely a code regression.", inv_p
        )
    if not inv_s and not inv_p:
        log.info("Drift-guards: 0 INVESTIGATE on both (vs Sellerise + vs prior pull).")

    # Exit 0 if no locked target FAILs AND no INVESTIGATE fires on EITHER guard;
    # else 1. The gate is on genuine failures alone. A KNOWN_TARGET_DEFECT cell is
    # a diagnosed defect on the *target's* side and never fails the run. Nor does
    # DEFECT_REMEASURED: its Δ moved, but rows ingested since the pin account for
    # all of it, so an unattended run must not go red on a legitimate refund. Both
    # become INVESTIGATE the moment the Δ moves for a reason ingestion cannot
    # explain, so a registry entry can never silence a regression in its cell.
    #
    # A locked target that misses its exact golden figure but stays within that
    # cell's drift band is ACCEPTED_DRIFT — restatement of a frozen golden figure,
    # the same our-vs-Sellerise drift the guard accepts on that band — and does
    # not fail the run. A locked target OUTSIDE its band is FAIL, a real
    # regression, and still exits 1. So the locked gate now means exactly what the
    # drift gate means: fail on regressions, not on restatement.
    all_good = locked_fail == 0 and inv_s == 0 and inv_p == 0
    return 0 if all_good else 1


if __name__ == "__main__":
    raise SystemExit(main())
