"""FastAPI read endpoint for the v1 P&L dashboard.

    GET /pnl?marketplace={US|CA|UK|AU|ALL}

Auth: a single shared password in env `DASHBOARD_PASSWORD`, compared **server-side** here
with a constant-time check. The password is never sent to or compared in the client.
Read-only: no table is written.
"""

from __future__ import annotations

import hmac
import os
import pathlib
import re
from datetime import date
from decimal import Decimal, InvalidOperation

import psycopg
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .pnl import (
    MARKETPLACES,
    SETTLED_MONTHS,
    _load_salary_overrides,
    assemble,
    assemble_range,
    daily_salary,
)

load_dotenv(pathlib.Path(__file__).resolve().parents[2] / ".env")

app = FastAPI(title="MYAMZTEAM P&L dashboard", docs_url=None, redoc_url=None)

# The Next.js dev server calls this API cross-origin. In prod set DASHBOARD_ORIGINS to an
# explicit comma-separated allowlist; for local dev (unset) allow any localhost port, so a
# Next fallback from :3000 to :3001 doesn't surface as an opaque CORS error.
_origins_env = os.environ.get("DASHBOARD_ORIGINS", "").strip()
_cors_kwargs = (
    {"allow_origins": [o.strip() for o in _origins_env.split(",") if o.strip()]}
    if _origins_env
    else {"allow_origin_regex": r"https?://localhost:\d+"}
)
app.add_middleware(
    CORSMiddleware,
    allow_methods=["GET", "PUT", "DELETE"],
    allow_headers=["X-Dashboard-Password", "Content-Type"],
    **_cors_kwargs,
)

_YM_RE = re.compile(r"^\d{4}-\d{2}$")

_VALID = set(MARKETPLACES) | {"ALL"}


def require_password(x_dashboard_password: str | None = Header(default=None)) -> None:
    """Constant-time check against DASHBOARD_PASSWORD. Fails closed if unset."""
    expected = os.environ.get("DASHBOARD_PASSWORD")
    if not expected:
        # Misconfiguration must not silently allow access.
        raise HTTPException(status_code=500, detail="dashboard auth not configured")
    supplied = x_dashboard_password or ""
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="unauthorized")


def _db_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    return url


@app.get("/pnl")
def get_pnl(
    marketplace: str = Query(default="US"),
    currency: str = Query(default="native"),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    _auth: None = Depends(require_password),
) -> dict:
    alias = marketplace.upper()
    if alias not in _VALID:
        raise HTTPException(status_code=400,
                            detail=f"marketplace must be one of {sorted(_VALID)}")
    view = currency.upper()
    if view not in ("NATIVE", "USD"):
        raise HTTPException(status_code=400, detail="currency must be 'native' or 'usd'")

    # Custom date range: both start and end (YYYY-MM-DD) → single-period range view.
    # Neither → the default month-as-column view. One-without-the-other is a bad request.
    if bool(start) != bool(end):
        raise HTTPException(status_code=400, detail="provide both start and end, or neither")
    range_bounds = None
    if start and end:
        try:
            s, e = date.fromisoformat(start), date.fromisoformat(end)
        except ValueError:
            raise HTTPException(status_code=400, detail="start/end must be YYYY-MM-DD dates")
        if e < s:
            raise HTTPException(status_code=400, detail="end date is before start date")
        range_bounds = (s, e)

    with psycopg.connect(_db_url()) as conn:
        if range_bounds:
            return assemble_range(conn, alias, range_bounds[0], range_bounds[1], view_currency=view)
        return assemble(conn, alias, view_currency=view)


class SalaryUpdate(BaseModel):
    year_month: str
    daily_amount: float


def _validate_ym(year_month: str) -> str:
    ym = year_month.strip()
    if not _YM_RE.match(ym):
        raise HTTPException(status_code=400, detail="year_month must be 'YYYY-MM'")
    return ym


@app.get("/salaries")
def get_salaries(_auth: None = Depends(require_password)) -> dict:
    """Effective daily salary per settled month, flagging which are DB overrides.

    Feeds the dashboard's salary editor. `daily_amount` is the override if one exists, else
    the code-level default; `is_override` distinguishes the two so the UI can offer a reset.
    """
    with psycopg.connect(_db_url()) as conn:
        overrides = _load_salary_overrides(conn)
    return {"months": [
        {"year_month": m,
         "daily_amount": float(daily_salary(m, overrides)),
         "is_override": m in overrides}
        for m in SETTLED_MONTHS
    ]}


@app.put("/salaries")
def put_salary(body: SalaryUpdate, _auth: None = Depends(require_password)) -> dict:
    """Upsert a month's daily-salary override (USD). Used by the ALL-view salary editor."""
    ym = _validate_ym(body.year_month)
    try:
        amount = Decimal(str(body.daily_amount))
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail="daily_amount must be a number")
    if amount < 0:
        raise HTTPException(status_code=400, detail="daily_amount must be non-negative")
    with psycopg.connect(_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO salary_override (year_month, daily_amount, updated_at)
                   VALUES (%s, %s, now())
                   ON CONFLICT (year_month)
                   DO UPDATE SET daily_amount = EXCLUDED.daily_amount, updated_at = now()""",
                (ym, amount),
            )
        conn.commit()
    return {"year_month": ym, "daily_amount": float(amount), "is_override": True}


@app.delete("/salaries/{year_month}")
def delete_salary(year_month: str, _auth: None = Depends(require_password)) -> dict:
    """Remove a month's override so it reverts to the code-level default."""
    ym = _validate_ym(year_month)
    with psycopg.connect(_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM salary_override WHERE year_month = %s", (ym,))
        conn.commit()
    return {"year_month": ym, "is_override": False}


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}
