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

import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import psycopg

from sync.reconcile import _SALES_TAX_LINES  # canonical salesTaxes leaves — reuse, don't re-derive

# Fixed book rates, native → USD — the FALLBACK when `fx_monthly_rates` has no row for a
# (currency, month). The live path is a per-month rate from `fx_monthly_rates` (populated by
# `sync.fx_rates`: monthly average of a daily feed). USD is always 1.
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

# Derived summary rows appended after the components. The full monthly profit (with
# reimbursements) is the emphasised bottom line; "no reimbursement" strips the
# Reimbursements row; the two "Daily" rows are month total ÷ calendar days — an AVERAGE, since
# COGS/fees are monthly-only, so no true per-day series exists.
GP_WITH_MONTHLY = "Gross Profit Monthly (with reimbursement)"
GP_NO_MONTHLY = "Gross Profit Monthly (no reimbursement)"
GP_WITH_DAILY = "Gross Profit Daily (with reimbursement)"
GP_NO_DAILY = "Gross Profit Daily (no reimbursement)"


def _days_in_month(ym: str) -> int:
    y, m = (int(x) for x in ym.split("-"))
    return calendar.monthrange(y, m)[1]

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


Rates = dict[tuple[str, str], Decimal]  # (currency, 'YYYY-MM') -> native→USD


def _load_monthly_rates(conn: psycopg.Connection) -> Rates:
    """Per-month native→USD rates from fx_monthly_rates (empty dict if the table is empty)."""
    out: Rates = {}
    with conn.cursor() as cur:
        cur.execute("SELECT currency, year_month, rate_to_usd FROM fx_monthly_rates")
        for ccy, ym, rate in cur.fetchall():
            out[(ccy, ym)] = rate
    return out


def _rate(ccy: str, ym: str, rates: Rates) -> Decimal:
    """native→USD for (ccy, month): the pulled monthly rate, else the fixed book fallback."""
    r = rates.get((ccy, ym))
    if r is not None:
        return r
    return BOOK_RATES_TO_USD.get(ccy, Decimal("1"))


def _convert(amount: Decimal, src: str, dst: str, ym: str, rates: Rates) -> Decimal:
    """Convert via USD at that month's rate. Unknown currency → book/passthrough (rate 1)."""
    return amount * _rate(src, ym, rates) / _rate(dst, ym, rates)


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


Accum = tuple  # (grid, sales_children, sf_children, of_children, ad_children)


def _accumulate(periods: list[str], pnl_rows, adspend_rows, target_ccy: str, rates: Rates) -> Accum:
    """Accumulate pre-shaped source rows into the grid + breakdowns over a generic `periods`
    list. Each pnl row is (period, rate_month, bucket, line_key, amount, ccy); each adspend row
    is (period, rate_month, ad_product, ccy, total). `rate_month` picks the FX rate; `period`
    is the column key. This is the ONE place the row/breakdown logic lives — the monthly view
    (periods = months, from pnl_monthly) and the range view (one period, from pnl_daily) both
    feed it.
    """
    z = lambda: {p: Decimal("0") for p in periods}
    grid = {r: z() for r in ROW_ORDER}
    sales_children: dict[str, dict[str, Decimal]] = {}
    sf_children = {name: z() for name in SF_CHILD_ORDER}
    of_children = {name: z() for name in OF_CHILD_ORDER}
    ad_children: dict[str, dict[str, Decimal]] = {}

    for period, rate_month, bucket, line_key, amount, ccy in pnl_rows:
        mapped = _map_row(bucket, line_key)
        if mapped is None:
            continue  # whitelist — passthrough/unknown never enters a row
        row, sign = mapped
        converted = _convert(amount, ccy, target_ccy, rate_month, rates) * sign
        grid[row][period] += converted
        # Sales breakdown: chargesObject leaves (sign +1) are the Sales sub-lines.
        if bucket == "chargesObject":
            sales_children.setdefault(line_key, z())[period] += converted
        # Selling Fees breakdown: fbaObject → FBA fees; feesObject → Referral vs Other.
        if row == "Selling Fees":
            if bucket == "fbaObject":
                sf_children["FBA fees"][period] += converted
            elif bucket == "feesObject":
                key = "Referral fees" if line_key in SF_REFERRAL_LEAVES else "Other fees"
                sf_children[key][period] += converted
        # Operational Fees breakdown: storageFee + expenses leaves rolled into groups.
        elif row == "Operational Fees":
            of_children[_of_group(bucket, line_key)][period] += converted
        # salesTaxes fold-in: buyer tax stays in Sales (collected) AND is booked as a remitted
        # cost in Selling Fees. Net-neutral to Profit; the amount is counted once.
        if bucket == "chargesObject" and line_key in _SALES_TAX_LINES:
            fold = _convert(amount, ccy, target_ccy, rate_month, rates) * -1
            grid["Selling Fees"][period] += fold
            sf_children["Taxes"][period] += fold

    for period, rate_month, ad_product, ccy, total in adspend_rows:
        spend = _convert(total, ccy, target_ccy, rate_month, rates) * -1
        grid["Ad Spend"][period] += spend
        ad_children.setdefault(ad_product or "Other", z())[period] += spend

    return grid, sales_children, sf_children, of_children, ad_children


def _finalize(alias: str, periods: list[str], period_days: dict[str, int], target_ccy: str,
              native_currency: str, accum: Accum, fx_rate_values: dict[str, Decimal] | None,
              extra: dict) -> dict:
    """Turn an accumulated grid into the display-ready response (rows, breakdowns, gross-profit
    rows, FX rate row), over a generic `periods` list with `period_days` for the daily rows."""
    grid, sales_children, sf_children, of_children, ad_children = accum

    def q(v: Decimal) -> float:
        return float(v.quantize(_CENT, rounding=ROUND_HALF_UP))

    def _sub_rows(children_grid: dict[str, dict[str, Decimal]]) -> list[dict]:
        """Ordered Sales sub-lines; any unlisted leaf is appended so children sum to Sales."""
        def one(name: str, pmap: dict[str, Decimal]) -> dict:
            vals = [pmap.get(p, Decimal("0")) for p in periods]
            return {"name": name, "values": [q(v) for v in vals], "total": q(sum(vals, Decimal("0")))}
        known = {key for _label, key in SALES_CHILDREN}
        out = [one(label, children_grid.get(key, {})) for label, key in SALES_CHILDREN]
        out += [one(key, pmap) for key, pmap in children_grid.items() if key not in known]
        return out

    def _named_rows(child_map, order, hints) -> list[dict]:
        """Sub-lines in fixed `order`, then any unlisted keys appended, each optional `hint`."""
        def one(name: str, pmap: dict[str, Decimal]) -> dict:
            vals = [pmap.get(p, Decimal("0")) for p in periods]
            row = {"name": name, "values": [q(v) for v in vals], "total": q(sum(vals, Decimal("0")))}
            if name in hints:
                row["hint"] = hints[name]
            return row
        out = [one(name, child_map.get(name, {})) for name in order]
        out += [one(name, pmap) for name, pmap in child_map.items() if name not in order]
        return out

    rows: list[dict] = []
    net = {p: Decimal("0") for p in periods}
    for r in ROW_ORDER:
        vals = [grid[r][p] for p in periods]
        for p in periods:
            net[p] += grid[r][p]
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

    # net[p] is the full profit (with reimbursements); "no reimbursement" strips the
    # Reimbursements row. Daily = period total ÷ its days; daily Total = grand total ÷ all days.
    reimb = grid["Reimbursements from AMZ"]
    with_reimb = {p: net[p] for p in periods}
    no_reimb = {p: net[p] - reimb[p] for p in periods}
    total_days = sum(period_days[p] for p in periods)

    def _monthly_row(name: str, vmap: dict[str, Decimal], *, is_net: bool = False) -> dict:
        vals = [vmap[p] for p in periods]
        row = {"name": name, "values": [q(v) for v in vals], "total": q(sum(vals, Decimal("0")))}
        if is_net:
            row["net"] = True
        return row

    def _daily_row(name: str, vmap: dict[str, Decimal]) -> dict:
        vals = [vmap[p] / period_days[p] for p in periods]
        total = sum(vmap.values(), Decimal("0")) / total_days
        return {"name": name, "values": [q(v) for v in vals], "total": q(total)}

    rows.append(_monthly_row(GP_WITH_MONTHLY, with_reimb, is_net=True))
    rows.append(_monthly_row(GP_NO_MONTHLY, no_reimb))
    rows.append(_daily_row(GP_WITH_DAILY, with_reimb))
    rows.append(_daily_row(GP_NO_DAILY, no_reimb))

    # FX reference row (non-USD views only). `rate: True` → client renders plain 4-dp numbers.
    if fx_rate_values is not None:
        _rq = lambda v: float(v.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
        vals = [fx_rate_values[p] for p in periods]
        avg = sum(vals, Decimal("0")) / len(vals)
        rows.append({"name": f"FX rate ({native_currency}→USD)",
                     "values": [_rq(v) for v in vals], "total": _rq(avg), "rate": True})

    return {"marketplace": alias, "currency": target_ccy, "native_currency": native_currency,
            "months": periods, "rows": rows, **extra}


def _resolve_target(alias: str, view_currency: str | None) -> tuple[list[str], str, str]:
    """(marketplace_ids, target_ccy, native_currency) for a view. Shared by month + range."""
    if alias == "ALL":
        return [mp for mp, _n in MARKETPLACES.values()], "USD", "USD"
    mp_id, native = MARKETPLACES[alias]
    target = "USD" if (view_currency or "").upper() == "USD" else native
    return [mp_id], target, native


def assemble(conn: psycopg.Connection, alias: str, view_currency: str | None = None) -> dict:
    """Month-as-column P&L for a marketplace alias or ALL (reads pnl_monthly).

    US and ALL are always USD. CA/UK/AU default to native; view_currency="USD" converts them
    to USD at each month's rate (the native↔USD toggle).
    """
    alias = alias.upper()
    if alias != "ALL" and alias not in MARKETPLACES:
        raise ValueError(f"unknown marketplace {alias!r}")
    rates = _load_monthly_rates(conn)
    mps, target_ccy, native_currency = _resolve_target(alias, view_currency)
    period_days = {m: _days_in_month(m) for m in SETTLED_MONTHS}

    pnl_rows, adspend_rows = [], []
    with conn.cursor() as cur:
        cur.execute("""SELECT year_month, bucket, line_key, amount, currency FROM pnl_monthly
                       WHERE marketplace_id = ANY(%s) AND year_month = ANY(%s)""",
                    (mps, SETTLED_MONTHS))
        pnl_rows = [(ym, ym, b, lk, Decimal(str(a)), c) for ym, b, lk, a, c in cur.fetchall()]
        cur.execute("""SELECT to_char(date,'YYYY-MM'), budget_currency, ad_product, SUM(total_cost)
                       FROM ad_spend_daily
                       WHERE marketplace_id = ANY(%s) AND to_char(date,'YYYY-MM') = ANY(%s)
                       GROUP BY 1, 2, 3""", (mps, SETTLED_MONTHS))
        adspend_rows = [(ym, ym, ap, c, Decimal(str(t))) for ym, c, ap, t in cur.fetchall()]

    accum = _accumulate(SETTLED_MONTHS, pnl_rows, adspend_rows, target_ccy, rates)
    fx = ({m: _rate(native_currency, m, rates) for m in SETTLED_MONTHS}
          if native_currency != "USD" else None)
    return _finalize(alias, SETTLED_MONTHS, period_days, target_ccy, native_currency, accum, fx, {})


def _range_label(start: date, end: date) -> str:
    if start.year == end.year:
        return f"{start.strftime('%b')} {start.day} – {end.strftime('%b')} {end.day}, {end.year}"
    return f"{start.strftime('%b')} {start.day}, {start.year} – {end.strftime('%b')} {end.day}, {end.year}"


def assemble_range(conn: psycopg.Connection, alias: str, start: date, end: date,
                   view_currency: str | None = None) -> dict:
    """Single-period P&L over the day range [start, end] inclusive (reads pnl_daily).

    Same rows/breakdowns/gross-profit as the monthly view, collapsed to one column. Each day
    converts at its month's rate; the FX row shows the day-weighted average over the range.
    """
    alias = alias.upper()
    if alias != "ALL" and alias not in MARKETPLACES:
        raise ValueError(f"unknown marketplace {alias!r}")
    if end < start:
        raise ValueError("end date is before start date")
    rates = _load_monthly_rates(conn)
    mps, target_ccy, native_currency = _resolve_target(alias, view_currency)
    P = "range"
    periods = [P]
    period_days = {P: (end - start).days + 1}

    pnl_rows, adspend_rows = [], []
    with conn.cursor() as cur:
        cur.execute("""SELECT to_char(date,'YYYY-MM'), bucket, line_key, currency, SUM(amount)
                       FROM pnl_daily
                       WHERE marketplace_id = ANY(%s) AND date BETWEEN %s AND %s
                       GROUP BY 1, 2, 3, 4""", (mps, start, end))
        pnl_rows = [(P, rm, b, lk, Decimal(str(a)), c) for rm, b, lk, c, a in cur.fetchall()]
        cur.execute("""SELECT to_char(date,'YYYY-MM'), budget_currency, ad_product, SUM(total_cost)
                       FROM ad_spend_daily
                       WHERE marketplace_id = ANY(%s) AND date BETWEEN %s AND %s
                       GROUP BY 1, 2, 3""", (mps, start, end))
        adspend_rows = [(P, rm, ap, c, Decimal(str(t))) for rm, c, ap, t in cur.fetchall()]

    accum = _accumulate(periods, pnl_rows, adspend_rows, target_ccy, rates)

    # FX row: day-weighted average of the month rates the range spans.
    fx = None
    if native_currency != "USD":
        d, wsum, n = start, Decimal("0"), 0
        while d <= end:
            wsum += _rate(native_currency, d.strftime("%Y-%m"), rates)
            n += 1
            d += timedelta(days=1)
        fx = {P: wsum / n}

    extra = {"is_range": True, "range_label": _range_label(start, end),
             "start": start.isoformat(), "end": end.isoformat()}
    return _finalize(alias, periods, period_days, target_ccy, native_currency, accum, fx, extra)
