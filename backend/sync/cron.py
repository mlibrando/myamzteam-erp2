"""sync.cron — thin monthly cron runner: ingest → reconcile → guards, exit-code alerting.

For each of US / CA / UK / AU in turn this runs the pipeline in the canonical order
(ingest → reconcile → guards), maps the guard verdict to a process exit code, and
logs a plain-text, greppable summary to stdout. It orchestrates the existing
entrypoints; it recomputes nothing and moves no reported number.

The exit-code contract (the whole design):

    INVESTIGATE (or a crash)   → non-zero. "Go look."
    DEFECT_REMEASURED          → zero, but logged prominently. Expected on the first
                                 run after an ingest; never fails the run (that is the
                                 cry-wolf trap S8 exists to prevent).
    ACCEPTED_DRIFT / KNOWN_TARGET_DEFECT / WITHIN_DRIFT / TRAILING → silent, zero.

The runner exits non-zero **iff** any marketplace hit INVESTIGATE or crashed. One
marketplace failing never skips the others — each is isolated so a crash is caught,
counted as that marketplace's failure, and the run still reports on all four.

Exit codes: 0 = OK, 1 = INVESTIGATE, 2 = a marketplace crashed (crash dominates).

Railway phase (not built here): a scheduled Railway job points at this runner. Because
the runner exits non-zero on INVESTIGATE/crash, Railway's native failed-job alerting is
the notifier — no notification code lives in the app. The only remaining decision is the
channel (Railway email / a webhook to Slack), made at deploy time. There is deliberately
no notification library, email/Slack code, digest formatter, or Railway config here;
getting the exit-code contract right now makes that alerting a config step, not new code.

DEPLOYMENT LANDMINE — reconcile() is not read-only: it COMMITS a pnl_monthly_snapshots
row per marketplace per call (the vs-prior-pull guard's baseline, read as MAX(pull_at)).
So every run of this cron advances that baseline. Railway must schedule this against the
production DB, but perturbation/CI testing must NOT: any test that drives the real
reconcile() writes a snapshot, and a perturbed value contaminates the baseline the next
production run trusts (it fires a spurious prior-pull INVESTIGATE). Test against a
separate DB, or make the test self-clean the pull_at it creates.
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import os
import pathlib
import re
import subprocess
import sys

import psycopg
from dotenv import load_dotenv

from .config import MARKETPLACE_ALIASES
from .reconcile import reconcile

log = logging.getLogger(__name__)

_BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
_AU_ALIAS = "AU"
_DEFAULT_ORDER = ("US", "CA", "UK", "AU")

# Exit codes — non-zero is the contract Railway reads; the distinct values are a
# convenience for a human reading the code, not load-bearing.
EXIT_OK = 0
EXIT_INVESTIGATE = 1
EXIT_CRASH = 2


@dataclasses.dataclass
class MarketResult:
    """One marketplace's outcome. `ok` is False iff it hit INVESTIGATE or crashed."""
    alias: str
    marketplace_id: str
    ok: bool = False
    crashed: bool = False
    ingested: bool = False
    counts: dict[str, int] = dataclasses.field(default_factory=dict)
    investigate_cells: list[dict] = dataclasses.field(default_factory=list)
    remeasured: int = 0
    error: str | None = None


def _now(db_url: str):
    """The database clock, so `ingested_at > t0` comparisons share a clock."""
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute("SELECT now()")
        return cur.fetchone()[0]


def _ingested_since(db_url: str, marketplace_id: str, since) -> bool:
    """Did Phase 1 land any new/changed rows for this marketplace this run?

    Both source tables stamp `ingested_at = now()` on upsert, so a row with
    `ingested_at > since` is one this run pulled. This is exactly the signal S8's
    DEFECT_REMEASURED legitimacy hinges on: a run that ingested nothing cannot
    legitimately remeasure a pin.
    """
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM sp_transactions "
            "WHERE marketplace_id = %s AND ingested_at > %s",
            (marketplace_id, since),
        )
        txns = cur.fetchone()[0]
        cur.execute(
            "SELECT count(*) FROM order_purchase_date "
            "WHERE marketplace_id = %s AND ingested_at > %s",
            (marketplace_id, since),
        )
        orders = cur.fetchone()[0]
    return (txns + orders) > 0


def _run_ingest(alias: str, start: str, orders_start: str, skip_orders: bool,
                timeout_s: int) -> None:
    """Run the committed pipeline (`python -m sync`) for one marketplace.

    Raises RuntimeError on a genuine failure. rc 0 (clean) and rc 2 (the pipeline's
    documented soft warning — unmapped pairs / missing SKUs) both mean it ran to
    completion; any other rc, or a timeout, is a crash for this marketplace.
    """
    cmd = [sys.executable, "-m", "sync", "--marketplace", alias,
           "--start", start, "--orders-start", orders_start, "--log-level", "WARNING"]
    if skip_orders:
        cmd.append("--skip-orders")
    proc = subprocess.run(cmd, cwd=_BACKEND_DIR, capture_output=True, text=True,
                          timeout=timeout_s)
    if proc.returncode not in (0, 2):
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-8:]
        raise RuntimeError(
            f"ingest exited {proc.returncode}\n" + "\n".join(tail)
        )


def _reconcile_sellerise(db_url: str, alias: str, marketplace_id: str) -> MarketResult:
    """US / CA / UK: run reconcile() in-process and read its structured result.

    The OK/fail verdict mirrors reconcile.main()'s exit gate exactly:
    no locked-target FAIL and no INVESTIGATE on either guard.
    """
    with psycopg.connect(db_url) as conn:
        # NB: reconcile() COMMITS a pnl_monthly_snapshots row (the vs-prior-pull
        # baseline) before returning — this call is NOT read-only; every run
        # advances the baseline. See the module docstring's deployment landmine.
        result = reconcile(conn, marketplace_id)

    inv_s = result["investigate_count"]
    inv_p = result["investigate_prior_count"]
    locked_fail = sum(1 for r in result["locked"] if r["status"] == "FAIL")

    counts: dict[str, int] = {}
    for r in result["drift_guard"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    for r in result["drift_vs_prior"]:
        if r["status"] == "INVESTIGATE":
            counts["INVESTIGATE_prior"] = counts.get("INVESTIGATE_prior", 0) + 1
    for r in result["locked"]:
        if r["status"] in ("ACCEPTED_DRIFT", "FAIL"):
            counts[f"LOCKED_{r['status']}"] = counts.get(f"LOCKED_{r['status']}", 0) + 1

    cells: list[dict] = []
    for r in result["drift_guard"]:
        if r["status"] == "INVESTIGATE":
            cells.append({"guard": "sellerise", "month": r["year_month"],
                          "bucket": r["bucket"], "sub_line": r["sub_line"],
                          "delta": r["delta"]})
    for r in result["drift_vs_prior"]:
        if r["status"] == "INVESTIGATE":
            cells.append({"guard": "prior-pull", "month": r["year_month"],
                          "bucket": r["bucket"], "sub_line": r["sub_line"],
                          "delta": r["delta"]})
    for r in result["locked"]:
        if r["status"] == "FAIL":
            cells.append({"guard": "locked-target", "month": r["year_month"],
                          "bucket": r["bucket"], "sub_line": r["sub_line"],
                          "delta": r["delta"]})

    return MarketResult(
        alias=alias, marketplace_id=marketplace_id,
        ok=(inv_s == 0 and inv_p == 0 and locked_fail == 0),
        counts=counts, investigate_cells=cells,
        remeasured=result["remeasured_count"],
    )


def _au_count(text: str, label: str) -> int:
    """Read a `**N <label>**` summary count from the AU report — fail loud if absent.

    The exit code keys on the CONTENT count, so a silent parse-miss reading 0 would
    turn a real AU regression green. Missing the line is treated as a crash instead.
    """
    m = re.search(rf"\*\*(\d+) {re.escape(label)}\*\*", text)
    if m is None:
        raise ValueError(f"AU report: could not find the '{label}' summary line")
    return int(m.group(1))


def _reconcile_au(alias: str, marketplace_id: str, timeout_s: int) -> MarketResult:
    """AU: run reconcile_au (subprocess) and read its report.

    AU's guard verdict lives only in the rendered report, so this reuses the real
    entrypoint and parses its own summary lines rather than reimplementing the
    classification. The report is written to a throwaway path so the committed
    `au_sellerboard_reconcile.md` is never touched. AU's INVESTIGATE-equivalent is a
    CONTENT flag (post-FX residual beyond the FX band that no pin explains).
    """
    scratch = _BACKEND_DIR / ".cron_au_report.md"
    cmd = [sys.executable, "-m", "sync.reconcile_au",
           "--report", str(scratch), "--log-level", "ERROR"]
    proc = subprocess.run(cmd, cwd=_BACKEND_DIR, capture_output=True, text=True,
                          timeout=timeout_s)
    try:
        scratch.unlink()
    except FileNotFoundError:
        pass
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-8:]
        raise RuntimeError(f"reconcile_au exited {proc.returncode}\n" + "\n".join(tail))

    text = proc.stdout
    content = _au_count(text, "CONTENT flags")
    remeasured = _au_count(text, "DEFECT_REMEASURED")
    ktd = _au_count(text, "KNOWN_TARGET_DEFECT")

    # CONTENT bullets sit between the CONTENT-flags header and the next section.
    cells: list[dict] = []
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if re.search(r"\*\*\d+ CONTENT flags\*\*", ln):
            for nxt in lines[i + 1:]:
                if nxt.startswith("## "):
                    break
                if nxt.startswith("- "):
                    cells.append({"guard": "sellerboard", "cell": nxt[2:].strip()})
            break

    return MarketResult(
        alias=alias, marketplace_id=marketplace_id,
        ok=(content == 0),
        counts={"CONTENT": content, "DEFECT_REMEASURED": remeasured,
                "KNOWN_TARGET_DEFECT": ktd},
        investigate_cells=cells, remeasured=remeasured,
    )


def run_marketplace(db_url: str, alias: str, *, do_ingest: bool, start: str,
                    orders_start: str, skip_orders: bool, ingest_timeout_s: int,
                    reconcile_timeout_s: int) -> MarketResult:
    """Ingest → reconcile → guards for one marketplace, isolating its failures.

    Any exception here is caught by the caller and recorded as this marketplace's
    crash; the run continues to the next marketplace regardless.
    """
    marketplace_id = MARKETPLACE_ALIASES.get(alias.upper(), alias)

    ingested = False
    if do_ingest:
        t0 = _now(db_url)
        _run_ingest(alias, start, orders_start, skip_orders, ingest_timeout_s)
        ingested = _ingested_since(db_url, marketplace_id, t0)

    if marketplace_id == MARKETPLACE_ALIASES[_AU_ALIAS]:
        res = _reconcile_au(alias, marketplace_id, reconcile_timeout_s)
    else:
        res = _reconcile_sellerise(db_url, alias, marketplace_id)
    res.ingested = ingested
    return res


def _emit_summary(results: list[MarketResult], ingest_mode: str) -> tuple[str, int]:
    """Print the plain-text, greppable run summary. Returns (result label, exit code)."""
    out = print  # stdout; Railway captures it

    out(f"=== cron: ingest -> reconcile -> guards | ingest={ingest_mode} ===")
    for r in results:
        if r.crashed:
            out(f"[{r.alias}] status=CRASH ingested={_yn(r.ingested)} | {r.error or 'unknown error'}")
            continue
        status = "OK" if r.ok else "INVESTIGATE"
        counts = " ".join(f"{k}={v}" for k, v in sorted(r.counts.items())) or "(none)"
        out(f"[{r.alias}] status={status} ingested={_yn(r.ingested)} | {counts}")

    # DEFECT_REMEASURED: legitimate only after an ingest; flag the impossible case.
    for r in results:
        if r.crashed or not r.remeasured:
            continue
        if r.ingested:
            out(f"DEFECT_REMEASURED: {r.alias} — expected: {r.remeasured} cell(s) remeasured "
                f"after ingest (pin Δ moved, newly-ingested rows account for all of it; re-pin).")
        else:
            out(f"DEFECT_REMEASURED: {r.alias} — ANOMALY: {r.remeasured} cell(s) on a run that "
                f"ingested nothing. Per S8 this should be impossible; investigate the pin horizon.")

    # INVESTIGATE cells — everything a human needs to start looking, no re-run required.
    inv = [(r, c) for r in results if not r.crashed for c in r.investigate_cells]
    if inv:
        out("INVESTIGATE cells:")
        for r, c in inv:
            if "cell" in c:  # AU
                out(f"  {r.alias} {c['cell']} ({c['guard']})")
            else:
                out(f"  {r.alias} {c['month']} {c['bucket']}.{c['sub_line']} "
                    f"Δ={c['delta']:+.2f} ({c['guard']})")

    crashed = any(r.crashed for r in results)
    investigate = any((not r.crashed and not r.ok) for r in results)
    if crashed:
        label, code = "CRASH", EXIT_CRASH
    elif investigate:
        label, code = "INVESTIGATE", EXIT_INVESTIGATE
    else:
        label, code = "OK", EXIT_OK
    out(f"RESULT: {label} | exit={code}")
    return label, code


def _yn(b: bool) -> str:
    return "yes" if b else "no"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync.cron")
    parser.add_argument("--marketplaces", default=",".join(_DEFAULT_ORDER),
                        help="Comma-separated aliases in run order (default: US,CA,UK,AU)")
    parser.add_argument("--skip-ingest", action="store_true",
                        help="Reconcile existing data only — no Phase 1 pull (safe no-op verification)")
    parser.add_argument("--start", default=None,
                        help="Finances ISO start passed to the pipeline (default: the pipeline's own)")
    parser.add_argument("--orders-start", default="2025-12-01T00:00:00Z")
    parser.add_argument("--skip-orders", action="store_true",
                        help="Skip the Orders sweep during ingest")
    parser.add_argument("--ingest-timeout-s", type=int, default=1800)
    parser.add_argument("--reconcile-timeout-s", type=int, default=600)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    load_dotenv(_BACKEND_DIR.parent / ".env")
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return EXIT_CRASH

    # The pipeline's own default start, unless overridden. Imported lazily so a
    # config edit to the default is picked up without duplicating it here.
    from .config import BACKFILL_START_ISO
    start = args.start or BACKFILL_START_ISO

    aliases = [a.strip() for a in args.marketplaces.split(",") if a.strip()]
    do_ingest = not args.skip_ingest
    results: list[MarketResult] = []
    for alias in aliases:
        log.info("── %s: ingest=%s → reconcile → guards ──", alias, do_ingest)
        try:
            res = run_marketplace(
                db_url, alias, do_ingest=do_ingest, start=start,
                orders_start=args.orders_start, skip_orders=args.skip_orders,
                ingest_timeout_s=args.ingest_timeout_s,
                reconcile_timeout_s=args.reconcile_timeout_s,
            )
        except Exception as exc:  # one marketplace's failure never drops the others
            log.exception("%s crashed", alias)
            marketplace_id = MARKETPLACE_ALIASES.get(alias.upper(), alias)
            res = MarketResult(alias=alias, marketplace_id=marketplace_id,
                               ok=False, crashed=True, error=f"{type(exc).__name__}: {exc}")
        results.append(res)

    ingest_mode = "no-ingest" if args.skip_ingest else "live"
    _label, code = _emit_summary(results, ingest_mode)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
