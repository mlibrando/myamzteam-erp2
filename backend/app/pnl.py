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

# Selling Fees breakdown. Unlike Sales (a single-bucket partition), this row is fed by three
# sources — feesObject, fbaObject, and the salesTaxes fold-in — so its children split by
# source: fbaObject → FBA fees; the salesTaxes fold-in → Taxes; and feesObject splits into the
# referral commission (Commission = settled, ReferralFee = pending) vs everything else
# (shipping/gift-wrap chargebacks, digital-services fee) → Other fees. Sums to the row exactly.
SF_REFERRAL_LEAVES = frozenset({"Commission", "ReferralFee"})
SF_CHILD_ORDER: list[str] = ["FBA fees", "Referral fees", "Other fees", "Taxes"]
SF_CHILD_HINTS: dict[str, str] = {
    "Other fees": "Shipping and gift-wrap chargebacks, plus digital services fees — "
                  "minor fee adjustments outside referral and FBA fees.",
}

# Operational Fees breakdown. This row is storageFee + every non-reimbursement `expenses`
# leaf — a ~30-leaf grab-bag, so children roll leaves up into fixed groups (a judgment call,
# unlike the Sales/Selling-Fees partitions). Unlisted leaves fall to "Other / adjustments" via
# _of_group's catch-all, so the children always sum to the row even as new fee types appear.
OF_CHILD_ORDER: list[str] = [
    "Storage", "Inbound / placement", "Removal & disposal",
    "Coupons & deals", "Subscription", "Other / adjustments",
]
OF_CHILD_HINTS: dict[str, str] = {
    "Other / adjustments": "Paid services fees plus a tail of small ledger adjustments, "
                           "retrocharges, and EPR/regulatory fees.",
}
_OF_INBOUND = frozenset({
    "ServiceFee.FBAInboundTransportationFee",
    "ServiceFee.FBAInboundConvenienceFee",
    "ServiceFee.FBAInboundTransportationProgramFee",
})
_OF_REMOVAL = frozenset({
    "ServiceFee.FBADisposalFee",
    "ServiceFee.FBARemovalFee",
    "ServiceFee.CustomerReturnHRRUnitFee",
})
_OF_COUPONS = frozenset({
    "ServiceFee.CouponParticipationFee",
    "ServiceFee.CouponPerformanceFee",
    "ServiceFee.DealParticipationFee",
    "ServiceFee.DealPerformanceFee",
})

# Ad Spend breakdown by ad_spend_daily.ad_product — Amazon's three ad types, in display
# order. Unlike the pnl_monthly rows this comes from a separate query; any future/unknown
# ad_product is appended (by raw value) so the children always sum to the Ad Spend row.
AD_CHILD_ORDER: list[str] = ["Sponsored Products", "Sponsored Brands", "Sponsored Display"]


def _of_group(bucket: str, line_key: str) -> str:
    """Roll one Operational Fees leaf into its display group; unknowns → Other / adjustments."""
    if bucket == "storageFee" or line_key == "ServiceFee.FBALongTermStorageFee":
        return "Storage"
    if line_key in _OF_INBOUND:
        return "Inbound / placement"
    if line_key.startswith("RemovalShipment.") or line_key in _OF_REMOVAL:
        return "Removal & disposal"
    if line_key in _OF_COUPONS:
        return "Coupons & deals"
    if line_key == "ServiceFee.Subscription":
        return "Subscription"
    return "Other / adjustments"

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
) -> tuple[dict[str, dict[str, Decimal]], dict[str, dict[str, Decimal]],
           dict[str, dict[str, Decimal]], dict[str, dict[str, Decimal]]]:
    """One marketplace's grid, every value converted to `target_ccy` by its own currency.

    Also returns three breakdowns, each a {child → month→Decimal} map that sums to its row:
    the Sales breakdown (keyed by raw chargesObject `line_key`), the Selling Fees breakdown
    (SF_CHILD_ORDER names), and the Operational Fees breakdown (OF_CHILD_ORDER names).
    """
    grid = _empty_grid()
    sales_children: dict[str, dict[str, Decimal]] = {}
    sf_children: dict[str, dict[str, Decimal]] = {
        name: {m: Decimal("0") for m in SETTLED_MONTHS} for name in SF_CHILD_ORDER
    }
    of_children: dict[str, dict[str, Decimal]] = {
        name: {m: Decimal("0") for m in SETTLED_MONTHS} for name in OF_CHILD_ORDER
    }
    ad_children: dict[str, dict[str, Decimal]] = {}
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
            # Selling Fees breakdown: fbaObject → FBA fees; feesObject → Referral vs Other.
            if row == "Selling Fees":
                if bucket == "fbaObject":
                    sf_children["FBA fees"][ym] += converted
                elif bucket == "feesObject":
                    key = "Referral fees" if line_key in SF_REFERRAL_LEAVES else "Other fees"
                    sf_children[key][ym] += converted
            # Operational Fees breakdown: storageFee + expenses leaves rolled into groups.
            elif row == "Operational Fees":
                of_children[_of_group(bucket, line_key)][ym] += converted
            # salesTaxes fold-in: buyer tax stays in Sales (collected) AND is booked as a
            # remitted cost in Selling Fees — matches Elena's sheet and the reconcile net
            # (revenue − salesTaxes − …). Net-neutral to Profit; the amount is counted once.
            if bucket == "chargesObject" and line_key in _SALES_TAX_LINES:
                fold = _convert(amount, ccy, target_ccy) * -1
                grid["Selling Fees"][ym] += fold
                sf_children["Taxes"][ym] += fold

        # Ad Spend is NOT in pnl_monthly — sum ad_spend_daily.total_cost (a positive cost,
        # in budget_currency) and negate it for display.
        cur.execute(
            """
            SELECT to_char(date, 'YYYY-MM') AS ym, budget_currency, ad_product, SUM(total_cost)
            FROM ad_spend_daily
            WHERE marketplace_id = %s AND to_char(date, 'YYYY-MM') = ANY(%s)
            GROUP BY 1, 2, 3
            """,
            (mp_id, SETTLED_MONTHS),
        )
        for ym, ccy, ad_product, total in cur.fetchall():
            spend = _convert(total, ccy, target_ccy) * -1
            grid["Ad Spend"][ym] += spend
            name = ad_product or "Other"
            ad_children.setdefault(
                name, {m: Decimal("0") for m in SETTLED_MONTHS}
            )[ym] += spend
    return grid, sales_children, sf_children, of_children, ad_children


def assemble(conn: psycopg.Connection, alias: str) -> dict:
    """Return the display-ready grid for a marketplace alias or ALL (USD)."""
    alias = alias.upper()
    if alias == "ALL":
        target_ccy = "USD"
        grid = _empty_grid()
        sales_children: dict[str, dict[str, Decimal]] = {}
        sf_children: dict[str, dict[str, Decimal]] = {
            name: {m: Decimal("0") for m in SETTLED_MONTHS} for name in SF_CHILD_ORDER
        }
        of_children: dict[str, dict[str, Decimal]] = {
            name: {m: Decimal("0") for m in SETTLED_MONTHS} for name in OF_CHILD_ORDER
        }
        ad_children: dict[str, dict[str, Decimal]] = {}
        for mp_id, _native in MARKETPLACES.values():
            one, one_children, one_sf, one_of, one_ad = _one_marketplace(conn, mp_id, "USD")
            for r in ROW_ORDER:
                for m in SETTLED_MONTHS:
                    grid[r][m] += one[r][m]
            for key, months in one_children.items():
                acc = sales_children.setdefault(key, {m: Decimal("0") for m in SETTLED_MONTHS})
                for m in SETTLED_MONTHS:
                    acc[m] += months.get(m, Decimal("0"))
            for name in SF_CHILD_ORDER:
                for m in SETTLED_MONTHS:
                    sf_children[name][m] += one_sf[name][m]
            for name in OF_CHILD_ORDER:
                for m in SETTLED_MONTHS:
                    of_children[name][m] += one_of[name][m]
            for name, months in one_ad.items():
                acc = ad_children.setdefault(name, {m: Decimal("0") for m in SETTLED_MONTHS})
                for m in SETTLED_MONTHS:
                    acc[m] += months.get(m, Decimal("0"))
    elif alias in MARKETPLACES:
        mp_id, target_ccy = MARKETPLACES[alias]
        grid, sales_children, sf_children, of_children, ad_children = _one_marketplace(conn, mp_id, target_ccy)
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

    def _named_rows(child_map: dict[str, dict[str, Decimal]], order: list[str],
                    hints: dict[str, str]) -> list[dict]:
        """Sub-lines in fixed `order`, then any unlisted keys appended (so children always sum
        to the row), each optionally carrying a `hint`."""
        def one(name: str, months: dict[str, Decimal]) -> dict:
            vals = [months.get(m, Decimal("0")) for m in SETTLED_MONTHS]
            row = {"name": name, "values": [q(v) for v in vals], "total": q(sum(vals, Decimal("0")))}
            if name in hints:
                row["hint"] = hints[name]
            return row

        out = [one(name, child_map.get(name, {})) for name in order]
        out += [one(name, months) for name, months in child_map.items() if name not in order]
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
        elif r == "Ad Spend":
            row["children"] = _named_rows(ad_children, AD_CHILD_ORDER, {})
        elif r == "Selling Fees":
            row["children"] = _named_rows(sf_children, SF_CHILD_ORDER, SF_CHILD_HINTS)
        elif r == "Operational Fees":
            row["children"] = _named_rows(of_children, OF_CHILD_ORDER, OF_CHILD_HINTS)
        rows.append(row)

    net_vals = [net[m] for m in SETTLED_MONTHS]
    rows.append({"name": NET_ROW, "values": [q(v) for v in net_vals],
                 "total": q(sum(net_vals, Decimal("0")))})

    return {"marketplace": alias, "currency": target_ccy,
            "months": SETTLED_MONTHS, "rows": rows}
