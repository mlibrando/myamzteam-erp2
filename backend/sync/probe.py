"""Empirical probe of listTransactions leaf `breakdownType` vocabulary.

Walks every stored transaction's raw_json for one marketplace, flattens the
breakdowns tree to leaves (via the same rule the pipeline uses), and reports the
distinct leaf `breakdownType` values grouped by (transactionType, transactionStatus).

Ground truth for Step 2 of the reconciliation refactor: the mapping dict in
`bucket_map.py` must be justified by output from this probe, not guessed.

Usage:
    python -m sync.probe [--marketplace US] [--output reference/data/probe_breakdowns.md]
"""

from __future__ import annotations

import argparse
import logging
import os
import pathlib
import sys
from collections import defaultdict
from decimal import Decimal
from statistics import median

import psycopg
from dotenv import load_dotenv

from .config import MARKETPLACE_ALIASES
from .finances import breakdown_leaves_for_txn

log = logging.getLogger(__name__)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def probe_marketplace(conn: psycopg.Connection, marketplace_id: str) -> dict:
    """Return {(txn_type, txn_status, breakdown_type): {occurrences, currency, samples, min, max, median}}.

    Iterates raw_json rather than sp_breakdowns so the probe is a re-flatten of the
    original API payload — the sp_breakdowns table already reflects one interpretation
    of the tree, so probing it would be circular.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                raw_json->>'transactionType'   AS txn_type,
                raw_json->>'transactionStatus' AS txn_status,
                raw_json
            FROM sp_transactions
            WHERE marketplace_id = %s
              AND is_deferred_release_event = false
            """,
            (marketplace_id,),
        )
        rows = cur.fetchall()

    # (txn_type, txn_status, breakdown_type) → { occurrences, currency, amounts[] }
    agg: dict[tuple[str, str, str], dict] = defaultdict(
        lambda: {"occurrences": 0, "currencies": set(), "amounts": []}
    )

    for txn_type, txn_status, raw in rows:
        txn_type = txn_type or "Unknown"
        txn_status = txn_status or "Unknown"
        for bt, amt, cc in breakdown_leaves_for_txn(raw):
            key = (txn_type, txn_status, bt)
            agg[key]["occurrences"] += 1
            agg[key]["currencies"].add(cc or "")
            agg[key]["amounts"].append(amt)

    # Compact into a result dict with derived stats.
    result: dict[tuple[str, str, str], dict] = {}
    for key, v in agg.items():
        amounts = sorted(v["amounts"])
        result[key] = {
            "occurrences": v["occurrences"],
            "currencies": ",".join(sorted(v["currencies"])),
            "min": amounts[0],
            "max": amounts[-1],
            "median": median(amounts),
            "samples": _pick_samples(amounts),
        }
    return result


def _pick_samples(sorted_amounts: list[Decimal]) -> list[Decimal]:
    """Return up to 3 illustrative sample amounts (min, median, max), deduplicated."""
    n = len(sorted_amounts)
    if n == 0:
        return []
    picks = [sorted_amounts[0], sorted_amounts[n // 2], sorted_amounts[-1]]
    seen: list[Decimal] = []
    for p in picks:
        if p not in seen:
            seen.append(p)
    return seen


def render_markdown(marketplace_id: str, result: dict, total_transactions: int) -> str:
    """Group by (txn_type, txn_status) and render a review-friendly Markdown table."""
    lines: list[str] = []
    lines.append(f"# Leaf breakdownType probe — marketplace {marketplace_id}")
    lines.append("")
    lines.append(f"Source: sp_transactions.raw_json (excluding is_deferred_release_event=true).")
    lines.append(f"Coverage: {total_transactions:,} transactions.")
    lines.append("")
    lines.append("Grouped by (transactionType, transactionStatus). RELEASED = settled amounts;")
    lines.append("DEFERRED = Amazon's estimate for orders not yet posted (see plan Ground Truth 2).")
    lines.append("")

    by_group: dict[tuple[str, str], list[tuple[str, dict]]] = defaultdict(list)
    for (txn_type, txn_status, bt), stats in result.items():
        by_group[(txn_type, txn_status)].append((bt, stats))

    for (txn_type, txn_status), items in sorted(by_group.items()):
        items.sort(key=lambda x: (-x[1]["occurrences"], x[0]))
        lines.append(f"## {txn_type} / {txn_status}")
        lines.append("")
        lines.append("| breakdownType | occ. | currency | min | median | max |")
        lines.append("|---|---:|---|---:|---:|---:|")
        for bt, stats in items:
            lines.append(
                f"| `{bt}` | {stats['occurrences']} | {stats['currencies']} | "
                f"{stats['min']:.2f} | {stats['median']:.2f} | {stats['max']:.2f} |"
            )
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync.probe")
    parser.add_argument("--marketplace", default="US")
    parser.add_argument(
        "--output",
        default=str(_REPO_ROOT / "reference" / "data" / "probe_breakdowns.md"),
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
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM sp_transactions WHERE marketplace_id = %s AND is_deferred_release_event = false",
                (marketplace_id,),
            )
            total = cur.fetchone()[0]
        result = probe_marketplace(conn, marketplace_id)

    md = render_markdown(marketplace_id, result, total)
    pathlib.Path(args.output).write_text(md)
    log.info("Wrote %s — %d (txn_type, txn_status, breakdown_type) combos across %d transactions",
             args.output, len(result), total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
