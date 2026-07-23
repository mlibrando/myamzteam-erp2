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

import psycopg
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .pnl import MARKETPLACES, assemble

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
    allow_methods=["GET"],
    allow_headers=["X-Dashboard-Password"],
    **_cors_kwargs,
)

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
    _auth: None = Depends(require_password),
) -> dict:
    alias = marketplace.upper()
    if alias not in _VALID:
        raise HTTPException(status_code=400,
                            detail=f"marketplace must be one of {sorted(_VALID)}")
    view = currency.upper()
    if view not in ("NATIVE", "USD"):
        raise HTTPException(status_code=400, detail="currency must be 'native' or 'usd'")
    with psycopg.connect(_db_url()) as conn:
        return assemble(conn, alias, view_currency=view)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}
