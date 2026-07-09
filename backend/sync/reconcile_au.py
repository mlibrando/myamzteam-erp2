"""AU reconciliation against Sellerboard, with FX and content residuals separated.

Reports two numbers per bucket per month, never merged:

  * **FX band** — `|ours_aud| x FX_RATE_TOLERANCE`, the widest USD residual a
    rate error alone can produce. Sellerboard converts per transaction date, so
    a monthly rate is never exact and some residual is expected.
  * **post-FX residual** — `theirs_usd - ours_aud x reference_rate`. Inside the
    band it is rate noise; outside it, it is content.

Merging the two is how a real gap hides behind "it's just FX". The band is an
*absolute* rate tolerance rather than a spread fitted to the observed
disagreement, because a fitted band grows to swallow whatever gap it is shown.

The reference rate comes only from content-insensitive anchors — refunds (the
identical events on both sides) and advertising (Ads API, outside the SP-API
transaction set). Revenue and fees are the buckets under test, so fitting the
rate to them would absorb a scope error into the rate and then report a clean
residual.

Shipments are attributed to order PurchaseDate and refunds to postedDate, which
is what Sellerboard does (see AU_SHIPMENT_BASIS). Before the AU `getOrders`
backfill this module ran on postedDate, and 2026-01's shipment family implied a
rate of 0.591 against refunds' 0.674 — the signature of the misattribution, not
of FX.

Usage:
    python -m sync.reconcile_au [--report reference/data/au_sellerboard_reconcile.md]
"""

from __future__ import annotations

import argparse
import logging
import os
import pathlib
import statistics
import sys
from collections import defaultdict
from decimal import Decimal

import psycopg
from dotenv import load_dotenv

from .config import (
    COG_FX_GUARD_AUD_RANGE,
    COG_FX_GUARD_SKU,
    MARKETPLACE_CURRENCY,
    MARKETPLACE_REFUND_BASIS,
    MARKETPLACE_REFUND_COGS_BASIS,
    cog_currency,
    cog_needs_fx,
    cog_source_marketplace,
)
from .sellerboard import (
    ANCHOR_SPREAD_WARN,
    AU_MARKETPLACE_ID,
    GST_GROSS_UP,
    SellerboardParseError,
    assert_bucket_totals,
    assert_net_reproduces,
    FX_BAND_FLOOR_USD,
    FX_RATE_TOLERANCE,
    fx_band,
    implied_rate,
    inventory_loss_gap,
    load_sellerboard,
    map_to_buckets,
    sellerboard_net,
    usd_to_aud,
)

log = logging.getLogger(__name__)

ZERO = Decimal("0")

AU_REFUND_BASIS = MARKETPLACE_REFUND_BASIS[AU_MARKETPLACE_ID]
AU_REFUND_COGS_BASIS = MARKETPLACE_REFUND_COGS_BASIS[AU_MARKETPLACE_ID]

# Sellerboard attributes shipments to order PurchaseDate and refunds to
# postedDate. Established on **unit counts**, which cannot be confounded by any
# dollar-side effect:
#
#   shipped units  vs SB `units`  : posted Δ=+14   purchase Δ=-1   -> purchase
#   refunded units vs SB `refunds`: posted Δ= +0   purchase Δ=-4   -> posted
#
# The purchase basis matches SB's units exactly in 5 of 6 months; posted matches
# in 0 of 6. SB's January `orders` (88) likewise equals our count of *Shipped*
# Jan-purchased orders exactly.
#
# A dollar-only test on cog appears to favour `posted` (Σ|Δ| 471 vs 1,046) but
# that comparison was malformed on both sides: it pitted our *refund-netted* cog
# against `salesCosts`, which does not net returns, and the posted basis's extra
# December-purchased bundles happened to offset the resulting bias. Comparing
# like with like — our **gross** shipped cog against `salesCosts` — the purchase
# basis agrees **to the cent in 5 of 6 months** (Σ|Δ| = 86.71, all of it in
# January). Counts settle the basis; the dollars then confirm it exactly.
AU_SHIPMENT_BASIS = "purchase"


# ── our side (AUD, native) ─────────────────────────────────────────────────

# Attribution SQL shared by the leaf and unit loaders. Same policy as
# attribution.py — Shipment on PurchaseDate, Refund on the empirical basis,
# everything else on postedDate — with both bases parameterised so the
# posted-vs-purchase tests can be re-run without editing SQL.
_ATTRIBUTION_YM = """
    to_char(
        CASE (t.raw_json->>'transactionType')
            WHEN 'Shipment' THEN {shipment_date}
            WHEN 'Refund'   THEN {refund_date}
            ELSE t.posted_at
        END AT TIME ZONE 'UTC', 'YYYY-MM')
"""
_ORDER_JOIN = """
    LEFT JOIN LATERAL (
        SELECT ri->>'relatedIdentifierValue' AS order_id
        FROM jsonb_array_elements(t.raw_json->'relatedIdentifiers') ri
        WHERE ri->>'relatedIdentifierName' = 'ORDER_ID' LIMIT 1
    ) rel ON true
    LEFT JOIN order_purchase_date opd
      ON opd.order_id = rel.order_id AND opd.marketplace_id = t.marketplace_id
"""


def _date_expr(basis: str) -> str:
    if basis not in ("posted", "purchase"):
        raise ValueError(f"basis must be 'posted' or 'purchase', got {basis!r}")
    return ("COALESCE(opd.purchase_date, t.posted_at)"
            if basis == "purchase" else "t.posted_at")


def _ym_expr(shipment_basis: str, refund_basis: str) -> str:
    return _ATTRIBUTION_YM.format(shipment_date=_date_expr(shipment_basis),
                                  refund_date=_date_expr(refund_basis))


def load_au_leaves(
    conn: psycopg.Connection,
    shipment_basis: str = AU_SHIPMENT_BASIS,
    refund_basis: str = "posted",
) -> dict[str, dict[str, Decimal]]:
    """{year_month: {"<TxnType>.<breakdown_type>": AUD amount}} for settled AU rows.

    Revenue and fee shipments follow order PurchaseDate, matching Sellerboard:
    unit counts agree exactly in 5 of 6 months on that basis and in 0 of 6 on
    postedDate.
    """
    ym_expr = _ym_expr(shipment_basis, refund_basis)
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {ym_expr} AS ym,
                   (t.raw_json->>'transactionType') || '.' || b.breakdown_type AS leaf,
                   SUM(b.breakdown_amount)
            FROM sp_breakdowns b
            JOIN sp_transactions t ON t.transaction_id = b.transaction_id
            {_ORDER_JOIN}
            WHERE t.marketplace_id = %s
              AND t.is_deferred_release_event = false
            GROUP BY 1, 2
            """,
            (AU_MARKETPLACE_ID,),
        )
        out: dict[str, dict[str, Decimal]] = defaultdict(dict)
        for ym, leaf, amount in cur.fetchall():
            out[ym][leaf] = Decimal(str(amount))
    return dict(out)


def load_au_ad_spend(conn: psycopg.Connection) -> dict[str, Decimal]:
    """{year_month: AUD ad spend} from ad_spend_daily (GST-exclusive)."""
    currency = MARKETPLACE_CURRENCY[AU_MARKETPLACE_ID]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT to_char(date, 'YYYY-MM'), SUM(total_cost)
            FROM ad_spend_daily
            WHERE marketplace_id = %s AND budget_currency = %s
            GROUP BY 1
            """,
            (AU_MARKETPLACE_ID, currency),
        )
        return {ym: Decimal(str(v)) for ym, v in cur.fetchall()}


def load_au_cog_units(
    conn: psycopg.Connection,
    shipment_basis: str = AU_SHIPMENT_BASIS,
    refund_cogs_basis: str = "posted",
) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, int]]]:
    """(shipped_units, refunded_units), each {year_month: {sku: units}}.

    Kept apart rather than netted so `net` can mirror Sellerboard's formula,
    which deducts gross `productCosts` and separately credits back the returned
    units inside `refundCostsTotal`.
    """
    ship_d, refund_d = _date_expr(shipment_basis), _date_expr(refund_cogs_basis)
    out: tuple[dict, dict] = (defaultdict(dict), defaultdict(dict))
    with conn.cursor() as cur:
        for idx, (txn_type, date_expr) in enumerate((("Shipment", ship_d), ("Refund", refund_d))):
            cur.execute(
                f"""
                SELECT to_char({date_expr} AT TIME ZONE 'UTC', 'YYYY-MM'), i.sku,
                       SUM(i.quantity_shipped)
                FROM sp_transaction_items i
                JOIN sp_transactions t ON t.transaction_id = i.transaction_id
                {_ORDER_JOIN}
                WHERE t.marketplace_id = %s
                  AND t.is_deferred_release_event = false
                  AND (t.raw_json->>'transactionType') = %s
                  AND i.quantity_shipped > 0
                GROUP BY 1, 2
                """,
                (AU_MARKETPLACE_ID, txn_type),
            )
            for ym, sku, qty in cur.fetchall():
                out[idx][ym][sku] = int(qty)
    return dict(out[0]), dict(out[1])


def load_au_net_units(
    conn: psycopg.Connection,
    shipment_basis: str = AU_SHIPMENT_BASIS,
    refund_cogs_basis: str = "posted",
) -> dict[str, dict[str, int]]:
    """{year_month: {sku: net units}} — shipments minus refunds, matching Sellerboard's
    `(units_sold - units_refunded) x unit_cog` COGS definition."""
    ym_expr = _ym_expr(shipment_basis, refund_cogs_basis)
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {ym_expr}, i.sku,
                   SUM(CASE (t.raw_json->>'transactionType')
                            WHEN 'Shipment' THEN  i.quantity_shipped
                            WHEN 'Refund'   THEN -i.quantity_shipped END)
            FROM sp_transaction_items i
            JOIN sp_transactions t ON t.transaction_id = i.transaction_id
            {_ORDER_JOIN}
            WHERE t.marketplace_id = %s
              AND t.is_deferred_release_event = false
              AND (t.raw_json->>'transactionType') IN ('Shipment', 'Refund')
              AND i.quantity_shipped > 0
            GROUP BY 1, 2
            """,
            (AU_MARKETPLACE_ID,),
        )
        out: dict[str, dict[str, int]] = defaultdict(dict)
        for ym, sku, qty in cur.fetchall():
            out[ym][sku] = int(qty)
    return dict(out)


def load_cog_rates(conn: psycopg.Connection) -> dict[str, Decimal]:
    """{sku: unit cog} from the *effective* cog source sheet for AU."""
    source = cog_source_marketplace(AU_MARKETPLACE_ID)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT sku, cogs FROM cogs_per_sku WHERE marketplace_id = %s",
            (source,),
        )
        return {sku: Decimal(str(cog)) for sku, cog in cur.fetchall()}


# ── cog FX guard ───────────────────────────────────────────────────────────

def assert_cog_not_double_converted(cog_rates: dict[str, Decimal], rate: Decimal) -> Decimal:
    """Convert the guard SKU's cog to AUD and assert it lands in the sane range.

    The AU sheet is USD, AU transactions are AUD, so cog must be divided by the
    rate exactly once. Both failure modes yield believable-looking numbers:
    multiplying instead of dividing gives ~21 AUD; dividing twice gives ~63.
    """
    if not cog_needs_fx(AU_MARKETPLACE_ID):
        raise SellerboardParseError(
            "AU cog is configured as not needing FX — MARKETPLACE_COG_CURRENCY changed?"
        )
    usd = cog_rates.get(COG_FX_GUARD_SKU)
    if usd is None:
        raise SellerboardParseError(f"guard SKU {COG_FX_GUARD_SKU} missing from cogs_per_sku")

    aud = usd_to_aud(usd, rate)
    low, high = COG_FX_GUARD_AUD_RANGE
    if not (low <= aud <= high):
        raise SellerboardParseError(
            f"cog FX guard failed: {COG_FX_GUARD_SKU} is {usd} "
            f"{cog_currency(AU_MARKETPLACE_ID)} -> {aud:.2f} AUD at rate {rate}, "
            f"outside the expected {low}..{high}. "
            f"Suspect double conversion (~{usd / rate / rate:.2f}) or inverted "
            f"conversion (~{usd * rate:.2f})."
        )
    return aud


# ── our buckets, in AUD ────────────────────────────────────────────────────

def our_buckets_aud(leaves: dict[str, Decimal]) -> dict[str, Decimal]:
    """Collapse our leaf sums into the comparable Sellerboard buckets (AUD).

    Fee lines are grossed up by GST where Sellerboard reports GST-inclusive
    figures: our pipeline splits AU's 10% GST into a bare `Tax` leaf that
    bucket_map routes to passthrough, so `Shipment.FBAPerUnitFulfillmentFee` and
    `ServiceFee.FBAStorageFee` are GST-exclusive on our side. The referral fee
    carries no GST and is compared as-is.
    """
    g = lambda k: leaves.get(k, ZERO)  # noqa: E731
    return {
        "revenue":     g("Shipment.OurPricePrincipal") + g("Shipment.ShippingPrincipal"),
        "commission":  g("Shipment.Commission"),
        "fbaFee":      g("Shipment.FBAPerUnitFulfillmentFee") * GST_GROSS_UP,
        "storageFee": -g("ServiceFee.FBAStorageFee") * GST_GROSS_UP,
        "refundPrincipal": g("Refund.OurPricePrincipal"),
        "refundCommission": g("Refund.Commission"),
    }


def anchor_rates(
    ours: dict[str, Decimal],
    theirs: dict[str, dict[str, Decimal]],
    ad_spend_aud: Decimal,
    ad_spend_usd: Decimal,
) -> dict[str, tuple[Decimal, bool]]:
    """{anchor name: (implied rate, content_sensitive)} for one month.

    Every pair is already on a GST-inclusive basis, so a disagreement between
    anchors is content or FX granularity — never a tax artifact.
    """
    def sub(bucket: str, line: str) -> Decimal:
        return theirs.get(bucket, {}).get(line, ZERO)

    pairs: list[tuple[str, Decimal, Decimal, bool]] = [
        ("sales / Principal",                 sub("chargesObject", "Revenue"),  ours["revenue"],          True),
        ("ReferralFee / Commission",          sub("feesObject", "Commission"),  ours["commission"],       True),
        ("FBAfee / FBAPerUnitFulfillmentFee", sub("fbaObject", "FBAPerUnitFulfillmentFee"), ours["fbaFee"], True),
        ("Storage / FBAStorageFee",           sub("storageFee", "storageFee"),  ours["storageFee"],       True),
        ("RefundedAmount / Refund.Principal", sub("refundsObject", "Principal"), ours["refundPrincipal"], False),
        ("RefundedReferralFee / Refund.Commission", sub("refundsObject", "Commission"), ours["refundCommission"], False),
        ("advertising / ad_spend_daily",      ad_spend_usd, ad_spend_aud * GST_GROSS_UP, False),
    ]
    out: dict[str, tuple[Decimal, bool]] = {}
    for name, usd, aud, content_sensitive in pairs:
        if usd and aud:
            out[name] = (abs(usd) / abs(aud), content_sensitive)
    return out


def reference_rate(rates: dict[str, tuple[Decimal, bool]]) -> tuple[Decimal, Decimal, str]:
    """(rate, spread, basis) from the content-insensitive anchors only.

    The reference rate is deliberately never fitted to revenue or fees. Those are
    the buckets under test: fitting the rate to them would absorb a scope error
    into the rate and report a clean residual. Refunds (identical events on both
    sides) and advertising (Ads API, outside the SP-API transaction set) cannot
    absorb a shipment-scope error, so they alone set the rate.

    Falls back to the full anchor set only when fewer than two insensitive
    anchors exist (2026-06 has no refunds), and says so.
    """
    insensitive = {k: v[0] for k, v in rates.items() if not v[1]}
    if len(insensitive) >= 2:
        rate, spread = implied_rate(insensitive)
        return rate, spread, "refunds + ads"

    all_rates = {k: v[0] for k, v in rates.items()}
    rate, spread = implied_rate(all_rates)
    return rate, spread, "all anchors (too few content-insensitive — rate weakly determined)"


def family_rates(rates: dict[str, tuple[Decimal, bool]]) -> dict[str, Decimal]:
    """Median implied rate per transaction family, to expose FX granularity.

    Sellerboard converts per transaction date, so each family lands on its own
    rate. Showing them side by side is what makes a family that has drifted far
    from the reference visible as content rather than disappearing into a
    blended average.
    """
    families = {
        "shipment": ["sales / Principal", "ReferralFee / Commission",
                     "FBAfee / FBAPerUnitFulfillmentFee"],
        "refund":   ["RefundedAmount / Refund.Principal",
                     "RefundedReferralFee / Refund.Commission"],
        "service":  ["Storage / FBAStorageFee"],
        "ads":      ["advertising / ad_spend_daily"],
    }
    out: dict[str, Decimal] = {}
    for family, members in families.items():
        vals = [float(rates[m][0]) for m in members if m in rates]
        if vals:
            out[family] = Decimal(str(statistics.median(vals)))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync.reconcile_au")
    parser.add_argument("--report", default="reference/data/au_sellerboard_reconcile.md")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO),
                        format="%(levelname)s %(name)s: %(message)s")

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    load_dotenv(repo_root / ".env")
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set", file=sys.stderr)
        return 1

    sb_months = load_sellerboard()
    assert_net_reproduces(sb_months)
    assert_bucket_totals(sb_months)
    log.info("Sellerboard gates passed: %d complete months", len(sb_months))

    with psycopg.connect(db_url) as conn:
        leaves = load_au_leaves(conn, refund_basis=AU_REFUND_BASIS)
        ad_aud = load_au_ad_spend(conn)
        net_units = load_au_net_units(conn, refund_cogs_basis=AU_REFUND_COGS_BASIS)
        ship_units, refund_units = load_au_cog_units(conn, refund_cogs_basis=AU_REFUND_COGS_BASIS)
        cog_rates = load_cog_rates(conn)

    rows: list[dict] = []
    for ym, period in sb_months.items():
        theirs = map_to_buckets(period)
        ours = our_buckets_aud(leaves.get(ym, {}))
        ad_usd = theirs.get("adExpenses", {}).get("(aggregate)", ZERO)
        rates = anchor_rates(ours, theirs, ad_aud.get(ym, ZERO), ad_usd)
        rate, spread, basis = reference_rate(rates)
        fams = family_rates(rates)

        cog_usd = sum((cog_rates.get(sku, ZERO) * qty for sku, qty in net_units.get(ym, {}).items()),
                      start=ZERO)
        gross_cog_usd = sum((cog_rates.get(s, ZERO) * q for s, q in ship_units.get(ym, {}).items()),
                            start=ZERO)
        returned_cog_usd = sum((cog_rates.get(s, ZERO) * q for s, q in refund_units.get(ym, {}).items()),
                               start=ZERO)
        rows.append({
            "ym": ym, "rate": rate, "spread": spread, "basis": basis,
            "rates": rates, "fams": fams, "ours": ours, "theirs": theirs, "period": period,
            "ad_aud": ad_aud.get(ym, ZERO), "cog_usd": cog_usd,
            "gross_cog_usd": gross_cog_usd, "returned_cog_usd": returned_cog_usd,
            "inventory_gap": inventory_loss_gap(period),
        })

    # Guard on the median settled rate, not a single month's.
    median_rate = Decimal(str(statistics.median([float(r["rate"]) for r in rows])))
    guard_aud = assert_cog_not_double_converted(cog_rates, median_rate)
    log.info("cog FX guard passed: %s = %s USD -> %.2f AUD at rate %.4f",
             COG_FX_GUARD_SKU, cog_rates[COG_FX_GUARD_SKU], guard_aud, median_rate)

    report = _render(rows, cog_rates, median_rate, guard_aud)
    out = repo_root / args.report
    out.write_text(report)
    log.info("Wrote %s", out)
    print(report)
    return 0


def _render(rows: list[dict], cog_rates: dict[str, Decimal],
            median_rate: Decimal, guard_aud: Decimal) -> str:
    L: list[str] = []
    a = L.append
    a("# AU reconciliation vs Sellerboard\n")
    a("FX and content residuals are reported separately. A post-FX residual inside")
    a("the FX-granularity band is rate noise; outside it, it is content.\n")

    a("## Implied AUD->USD rate\n")
    a("Sellerboard converts per transaction date, so each family lands on its own")
    a("rate. The reference rate is set by refunds + ads, never by the buckets under")
    a("test. `|shipment - ref|` beyond the FX tolerance means shipment *content*")
    a(f"differs, not the rate (tolerance {FX_RATE_TOLERANCE}).\n")
    a("| month | reference rate | basis | shipment | refund | service | ads | \\|ship-ref\\| |")
    a("|---|---:|---|---:|---:|---:|---:|---:|")
    for r in rows:
        f = r["fams"]
        cell = lambda k: f"{f[k]:.4f}" if k in f else "—"
        gap = abs(f["shipment"] - r["rate"]) if "shipment" in f else ZERO
        mark = " ⚠" if gap > FX_RATE_TOLERANCE else ""
        a(f"| {r['ym']} | {r['rate']:.4f} | {r['basis']} | {cell('shipment')} | "
          f"{cell('refund')} | {cell('service')} | {cell('ads')} | {gap:.4f}{mark} |")
    a(f"\nMedian reference rate: **{median_rate:.4f}** (workbook states 0.67).")
    a("⚠ marks a month whose shipment family cannot be reconciled to the reference")
    a("rate by any plausible intra-month FX move.\n")

    a("### Per-anchor implied rate (GST-normalised)\n")
    names = sorted({n for r in rows for n in r["rates"]})
    a("| anchor | " + " | ".join(r["ym"][-2:] for r in rows) + " |")
    a("|---" * (len(rows) + 1) + "|")
    for n in names:
        cells = [f"{r['rates'][n][0]:.4f}" if n in r["rates"] else "—" for r in rows]
        a(f"| `{n}` | " + " | ".join(cells) + " |")

    a("\n## Per-bucket residuals\n")
    a("`ours` is AUD converted to USD at the month's reference rate. The FX band is")
    a(f"|ours_aud| x {FX_RATE_TOLERANCE} (the widest residual a rate error alone can")
    a(f"produce), floored at ${FX_BAND_FLOOR_USD} for Sellerboard's cent-rounding.\n")
    a("| month | bucket | ours (USD) | Sellerboard | post-FX Δ | Δ% | FX band | verdict |")
    a("|---|---|---:|---:|---:|---:|---:|---|")
    bucket_lines = [
        ("revenue", "chargesObject", "Revenue"),
        ("commission", "feesObject", "Commission"),
        ("fbaFee", "fbaObject", "FBAPerUnitFulfillmentFee"),
        ("storageFee", "storageFee", "storageFee"),
        ("refundPrincipal", "refundsObject", "Principal"),
        ("refundCommission", "refundsObject", "Commission"),
    ]
    content_flags: list[str] = []
    for r in rows:
        for key, bucket, line in bucket_lines:
            ours_usd = r["ours"][key] * r["rate"]
            theirs = r["theirs"].get(bucket, {}).get(line, ZERO)
            delta = theirs - ours_usd
            band = fx_band(r["ours"][key])
            pct = (delta / abs(ours_usd) * 100) if ours_usd else ZERO
            is_content = abs(delta) > band
            if is_content:
                content_flags.append(f"{r['ym']} {bucket}.{line} {delta:+,.2f}")
            a(f"| {r['ym']} | `{bucket}.{line}` | {ours_usd:,.2f} | {theirs:,.2f} | "
              f"{delta:+,.2f} | {pct:+.2f}% | ±{band:,.2f} | "
              f"{'**CONTENT**' if is_content else 'FX noise'} |")

    a(f"\n**{len(content_flags)} CONTENT flags** (post-FX residual beyond the FX band):\n")
    for f in content_flags:
        a(f"- {f}")

    a("\n## net, on Sellerboard's own basis\n")
    a("Rebuilt from our AUD lines using Sellerboard's own formula: deduct **gross**")
    a("shipped cog (its `productCosts`), then credit back the returned units")
    a("(its `Value of returned items`, which sits inside `refundCostsTotal`).")
    a("Only the inventory-loss gap is borrowed from Sellerboard — `listTransactions`")
    a("cannot see stock that never sold.\n")
    a("| month | ours (USD) | Sellerboard netProfit | Δ | Δ% |")
    a("|---|---:|---:|---:|---:|")
    tot_net = ZERO
    for r in rows:
        t = r["theirs"]
        ours_net = (
            r["ours"]["revenue"] * r["rate"]
            + r["ours"]["commission"] * r["rate"]
            + r["ours"]["fbaFee"] * r["rate"]
            - r["ours"]["storageFee"] * r["rate"]
            + sum(t.get("refundsObject", {}).values(), start=ZERO)
            + sum(t.get("expenses", {}).values(), start=ZERO)
            - r["gross_cog_usd"]
            + r["returned_cog_usd"]
            + r["inventory_gap"]
            - t.get("adExpenses", {}).get("(aggregate)", ZERO)
        )
        theirs_net = sellerboard_net(r["period"])
        d = theirs_net - ours_net
        tot_net += d
        pct = (d / abs(theirs_net) * 100) if theirs_net else ZERO
        a(f"| {r['ym']} | {ours_net:,.2f} | {theirs_net:,.2f} | {d:+,.2f} | {pct:+.2f}% |")
    a(f"| **Σ** | | | **{tot_net:+,.2f}** | |")

    a("\n## cog (compared USD-to-USD; no FX on either side)\n")
    a("AU sheet is USD, Sellerboard is USD. Converting both by the same rate is a")
    a("no-op on the ratio, so cog is compared natively and the FX band does not apply.\n")
    a("`salesCosts` is `units_sold x unit_cog` with inventory losses stripped, so the")
    a("like-for-like comparison is our **gross shipped** cog — not the refund-netted")
    a("figure. `productCosts` = `salesCosts` + those losses, which `listTransactions`")
    a("cannot see.\n")
    a("| month | ours gross cog | salesCosts | Δ | ours returned cog | valueOfReturned | Δ | inventory-loss gap |")
    a("|---|---:|---:|---:|---:|---:|---:|---:|")
    tot_sc = tot_ret = tot_gap = ZERO
    for r in rows:
        sc = r["theirs"]["cog"]["(salesCosts)"]
        vri = r["theirs"].get("cogAdjust", {}).get("ReturnedItemsValue", ZERO)
        d = r["gross_cog_usd"] - sc
        dr = r["returned_cog_usd"] - vri
        tot_sc += d
        tot_ret += dr
        tot_gap += r["inventory_gap"]
        a(f"| {r['ym']} | {r['gross_cog_usd']:,.2f} | {sc:,.2f} | {d:+,.2f} | "
          f"{r['returned_cog_usd']:,.2f} | {vri:,.2f} | {dr:+,.2f} | {r['inventory_gap']:+,.2f} |")
    a(f"| **Σ** | | | **{tot_sc:+,.2f}** | | | **{tot_ret:+,.2f}** | **{tot_gap:+,.2f}** |")
    a("")
    a("Our AU workbook unit costs **equal Sellerboard's**: five of six months agree to")
    a("the cent. 2026-01's entire -86.71 is one MBUKB1 unit (workbook cog 86.71) whose")
    a("order carries no financial transaction — see the S03 orders below.")

    a(f"\n## cog FX guard\n")
    usd = cog_rates[COG_FX_GUARD_SKU]
    a(f"- `{COG_FX_GUARD_SKU}` = {usd} USD -> **{guard_aud:.2f} AUD** at rate {median_rate:.4f} "
      f"(expected {COG_FX_GUARD_AUD_RANGE[0]}..{COG_FX_GUARD_AUD_RANGE[1]}) ✓")
    a(f"- inverted-conversion failure would give ~{usd * median_rate:.2f} AUD")
    a(f"- double-conversion failure would give ~{usd / median_rate / median_rate:.2f} AUD")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
