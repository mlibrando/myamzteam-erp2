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

from sync.reconcile import _SALES_TAX_LINES  # canonical salesTaxes leaves — reuse, don't re-derive

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
NET_ROW = "Profit"

# Sales breakdown: display label → chargesObject `line_key`, in display order. The Sales row
# IS the chargesObject bucket (every leaf maps to Sales, sign +1), so these children
# partition it exactly. Any leaf not listed here is still emitted (appended by raw key) so
# the children always sum to the Sales row — the invariant can't silently break.
#
# No plain `Shipping` line: our pipeline never emits one (ShippingPrincipal routes to
# ShippingCharge, and net US shipping is ~$0 — Principal offset by ShippingDiscount→Promotion
# and ShippingChargeback→Selling Fees). Sellerise's small "Shipping" figure is a month-boundary
# timing residual on that net-zero quantity, not a distinct amount in our data.
SALES_CHILDREN: list[tuple[str, str]] = [
    ("Product sales",  "Principal"),
    ("Tax",            "Tax"),
    ("Promotion",      "Promotion"),
    ("Shipping charge", "ShippingCharge"),
    ("Shipping tax",   "ShippingTax"),
    ("Gift wrap",      "GiftWrap"),
    ("Gift wrap tax",  "GiftWrapTax"),
]

# Reimbursement family (expenses bucket): the money-IN leaf and its reversal/clawback
# (money-out) BOTH net under Reimbursements — Elena's decision that the reversal is a
# reimbursement clawback, not an operational fee. Matched by an explicit key set (not a
# prefix) so the money-in leaf can never fall through to Operational Fees.
REIMB_LEAVES = frozenset({
    "FBAInventoryReimbursement.FBAInventoryReimbursement",  # money in  (+)
    "FBAInventoryReimbursement.FBAReversedReimbursement",   # reversal  (−)
})

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
        if line_key in REIMB_LEAVES:
            return ("Reimbursements from AMZ", 1)  # money-in (+) and reversal (−) net here
        return ("Operational Fees", 1)             # every other expenses leaf
    if bucket == "refundsObject":
        return ("Refunds", 1)                    # stored −
    return None                                  # passthrough & anything unknown → ignored


def _empty_grid() -> dict[str, dict[str, Decimal]]:
    return {r: {m: Decimal("0") for m in SETTLED_MONTHS} for r in ROW_ORDER}


def _one_marketplace(
    conn: psycopg.Connection, mp_id: str, target_ccy: str
) -> tuple[dict[str, dict[str, Decimal]], dict[str, dict[str, Decimal]]]:
    """One marketplace's grid, every value converted to `target_ccy` by its own currency.

    Also returns the Sales breakdown keyed by raw chargesObject `line_key` (each a
    month→Decimal map), which partitions the Sales row exactly.
    """
    grid = _empty_grid()
    sales_children: dict[str, dict[str, Decimal]] = {}
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
            converted = _convert(amount, ccy, target_ccy) * sign
            grid[row][ym] += converted
            # Sales breakdown: chargesObject leaves (sign +1) are the Sales sub-lines.
            if bucket == "chargesObject":
                sales_children.setdefault(
                    line_key, {m: Decimal("0") for m in SETTLED_MONTHS}
                )[ym] += converted
            # salesTaxes fold-in: buyer tax stays in Sales (collected) AND is booked as a
            # remitted cost in Selling Fees — matches Elena's sheet and the reconcile net
            # (revenue − salesTaxes − …). Net-neutral to Profit; the amount is counted once.
            if bucket == "chargesObject" and line_key in _SALES_TAX_LINES:
                grid["Selling Fees"][ym] += _convert(amount, ccy, target_ccy) * -1

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
    return grid, sales_children


def assemble(conn: psycopg.Connection, alias: str) -> dict:
    """Return the display-ready grid for a marketplace alias or ALL (USD)."""
    alias = alias.upper()
    if alias == "ALL":
        target_ccy = "USD"
        grid = _empty_grid()
        sales_children: dict[str, dict[str, Decimal]] = {}
        for mp_id, _native in MARKETPLACES.values():
            one, one_children = _one_marketplace(conn, mp_id, "USD")
            for r in ROW_ORDER:
                for m in SETTLED_MONTHS:
                    grid[r][m] += one[r][m]
            for key, months in one_children.items():
                acc = sales_children.setdefault(key, {m: Decimal("0") for m in SETTLED_MONTHS})
                for m in SETTLED_MONTHS:
                    acc[m] += months.get(m, Decimal("0"))
    elif alias in MARKETPLACES:
        mp_id, target_ccy = MARKETPLACES[alias]
        grid, sales_children = _one_marketplace(conn, mp_id, target_ccy)
    else:
        raise ValueError(f"unknown marketplace {alias!r}")

    def q(v: Decimal) -> float:
        return float(v.quantize(_CENT, rounding=ROUND_HALF_UP))

    def _sub_rows(children_grid: dict[str, dict[str, Decimal]]) -> list[dict]:
        """Ordered Sales sub-lines; any unlisted leaf is appended so children sum to Sales."""
        def one(name: str, months: dict[str, Decimal]) -> dict:
            vals = [months.get(m, Decimal("0")) for m in SETTLED_MONTHS]
            return {"name": name, "values": [q(v) for v in vals], "total": q(sum(vals, Decimal("0")))}

        known = {key for _label, key in SALES_CHILDREN}
        out = [one(label, children_grid.get(key, {})) for label, key in SALES_CHILDREN]
        out += [one(key, months) for key, months in children_grid.items() if key not in known]
        return out

    rows: list[dict] = []
    net = {m: Decimal("0") for m in SETTLED_MONTHS}
    for r in ROW_ORDER:
        vals = [grid[r][m] for m in SETTLED_MONTHS]
        for m in SETTLED_MONTHS:
            net[m] += grid[r][m]
        row = {"name": r, "values": [q(v) for v in vals], "total": q(sum(vals, Decimal("0")))}
        if r == "Sales":
            row["children"] = _sub_rows(sales_children)
        rows.append(row)

    net_vals = [net[m] for m in SETTLED_MONTHS]
    rows.append({"name": NET_ROW, "values": [q(v) for v in net_vals],
                 "total": q(sum(net_vals, Decimal("0")))})

    return {"marketplace": alias, "currency": target_ccy,
            "months": SETTLED_MONTHS, "rows": rows}
