"""Server-side assembly of the month-as-column P&L grid.

The bucket→row mapping is a WHITELIST (see reference/data/pnl_dashboard_probe.md §3 and
DASHBOARD.md): only the buckets below map to rows; everything else — the entire
`passthrough` bucket, including the +$100k `Transfer.FundTransfer` settlement movement —
is ignored, so a future passthrough leaf can never leak into a P&L row.

Currency is driven by each value's own stored `currency` (pnl_monthly is per-row;
ad_spend_daily carries `budget_currency`). Converting by the value's own currency makes
the CA/AU double-conversion trap structurally impossible: CA/AU `cog` is stored in USD, so
it converts as USD (a no-op into the USD view; USD→native in the native view) and is never
treated as CAD/AUD.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

import psycopg

# Elena's FIXED book rates, native → USD. These are her sheet's rates (NOT the reconcile's
# implied FX); used only for the ALL(USD) view and to show CA/AU's USD cog in native.
BOOK_RATES_TO_USD: dict[str, Decimal] = {
    "USD": Decimal("1"),
    "GBP": Decimal("1.34"),
    "CAD": Decimal("0.71"),
    "AUD": Decimal("0.69"),
}

# alias -> (marketplace_id, native currency)
MARKETPLACES: dict[str, tuple[str, str]] = {
    "US": ("ATVPDKIKX0DER", "USD"),
    "CA": ("A2EUQ1WTGCTBG2", "CAD"),
    "UK": ("A1F83G8C2ARO7P", "GBP"),
    "AU": ("A39IBJ37TRP1C6", "AUD"),
}

SETTLED_MONTHS: list[str] = [f"2026-{m:02d}" for m in range(1, 7)]  # Jan–Jun 2026

ROW_ORDER: list[str] = [
    "Sales", "COGS", "Ad Spend", "Selling Fees",
    "Operational Fees", "Refunds", "Reimbursements from AMZ",
]
NET_ROW = "Net"

# The single expenses leaf that is money-IN (Reimbursements). Every other expenses leaf —
# including FBAReversedReimbursement (money out) — is Operational Fees.
REIMB_LEAF = "FBAInventoryReimbursement.FBAInventoryReimbursement"

_CENT = Decimal("0.01")


def _convert(amount: Decimal, src: str, dst: str) -> Decimal:
    """Convert via USD at Elena's book rates. Unknown currency → passthrough (rate 1)."""
    r_src = BOOK_RATES_TO_USD.get(src, Decimal("1"))
    r_dst = BOOK_RATES_TO_USD.get(dst, Decimal("1"))
    return amount * r_src / r_dst


def _map_row(bucket: str, line_key: str) -> tuple[str, int] | None:
    """Whitelist: (row_name, sign) or None to ignore.

    sign is applied to the STORED amount to produce a display value where costs are
    negative and net is a plain column sum. `cog` is stored positive, so COGS negates it;
    everything else is stored with its natural sign and is used as-is.
    """
    if bucket == "chargesObject":
        return ("Sales", 1)                      # stored + (revenue)
    if bucket == "cog":
        return ("COGS", -1)                      # stored +, shown as a cost
    if bucket in ("feesObject", "fbaObject"):
        return ("Selling Fees", 1)               # stored −
    if bucket == "storageFee":
        return ("Operational Fees", 1)           # stored −
    if bucket == "expenses":
        if line_key == REIMB_LEAF:
            return ("Reimbursements from AMZ", 1)  # stored + (money in)
        return ("Operational Fees", 1)             # everything else, incl. money-out clawbacks
    if bucket == "refundsObject":
        return ("Refunds", 1)                    # stored −
    return None                                  # passthrough & anything unknown → ignored


def _empty_grid() -> dict[str, dict[str, Decimal]]:
    return {r: {m: Decimal("0") for m in SETTLED_MONTHS} for r in ROW_ORDER}


def _one_marketplace(conn: psycopg.Connection, mp_id: str, target_ccy: str) -> dict[str, dict[str, Decimal]]:
    """One marketplace's grid, every value converted to `target_ccy` by its own currency."""
    grid = _empty_grid()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT year_month, bucket, line_key, amount, currency
            FROM pnl_monthly
            WHERE marketplace_id = %s AND year_month = ANY(%s)
            """,
            (mp_id, SETTLED_MONTHS),
        )
        for ym, bucket, line_key, amount, ccy in cur.fetchall():
            mapped = _map_row(bucket, line_key)
            if mapped is None:
                continue  # whitelist — passthrough/unknown never enters a row
            row, sign = mapped
            grid[row][ym] += _convert(amount, ccy, target_ccy) * sign

        # Ad Spend is NOT in pnl_monthly — sum ad_spend_daily.total_cost (a positive cost,
        # in budget_currency) and negate it for display.
        cur.execute(
            """
            SELECT to_char(date, 'YYYY-MM') AS ym, budget_currency, SUM(total_cost)
            FROM ad_spend_daily
            WHERE marketplace_id = %s AND to_char(date, 'YYYY-MM') = ANY(%s)
            GROUP BY 1, 2
            """,
            (mp_id, SETTLED_MONTHS),
        )
        for ym, ccy, total in cur.fetchall():
            grid["Ad Spend"][ym] += _convert(total, ccy, target_ccy) * -1
    return grid


def assemble(conn: psycopg.Connection, alias: str) -> dict:
    """Return the display-ready grid for a marketplace alias or ALL (USD)."""
    alias = alias.upper()
    if alias == "ALL":
        target_ccy = "USD"
        grid = _empty_grid()
        for mp_id, _native in MARKETPLACES.values():
            one = _one_marketplace(conn, mp_id, "USD")
            for r in ROW_ORDER:
                for m in SETTLED_MONTHS:
                    grid[r][m] += one[r][m]
    elif alias in MARKETPLACES:
        mp_id, target_ccy = MARKETPLACES[alias]
        grid = _one_marketplace(conn, mp_id, target_ccy)
    else:
        raise ValueError(f"unknown marketplace {alias!r}")

    def q(v: Decimal) -> float:
        return float(v.quantize(_CENT, rounding=ROUND_HALF_UP))

    rows: list[dict] = []
    net = {m: Decimal("0") for m in SETTLED_MONTHS}
    for r in ROW_ORDER:
        vals = [grid[r][m] for m in SETTLED_MONTHS]
        for m in SETTLED_MONTHS:
            net[m] += grid[r][m]
        rows.append({"name": r, "values": [q(v) for v in vals], "total": q(sum(vals, Decimal("0")))})

    net_vals = [net[m] for m in SETTLED_MONTHS]
    rows.append({"name": NET_ROW, "values": [q(v) for v in net_vals],
                 "total": q(sum(net_vals, Decimal("0")))})

    return {"marketplace": alias, "currency": target_ccy,
            "months": SETTLED_MONTHS, "rows": rows}
