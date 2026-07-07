"""Static config: marketplace metadata + credential mapping for python-amazon-sp-api.

Regional routing (host + AWS region) is handled by the library's `Marketplaces`
enum — we just map our marketplace_id string to the corresponding enum member.

Refresh tokens are grouped per region (one token covers every marketplace in
that region), so we keep a small marketplace_id → refresh_token_env mapping.
"""

from __future__ import annotations

import os
import pathlib

from sp_api.base import Marketplaces

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

# COGS workbook path (relative to repo root).
COGS_XLSX = _REPO_ROOT / "reference" / "data" / "COGS_Magical_Butter_1.xlsx"

US_MARKETPLACE_ID = "ATVPDKIKX0DER"

MARKETPLACE_ALIASES: dict[str, str] = {
    "US": "ATVPDKIKX0DER",
    "CA": "A2EUQ1WTGCTBG2",
    "UK": "A1F83G8C2ARO7P",
    "AU": "A39IBJ37TRP1C6",
}

# Marketplace → native currency (per the "no FX conversion" decision).
# This drives the `budget_currency` filter when loading ad_spend_daily for
# per-marketplace reconciliation.
MARKETPLACE_CURRENCY: dict[str, str] = {
    "ATVPDKIKX0DER": "USD",
    "A2EUQ1WTGCTBG2": "CAD",
    "A1F83G8C2ARO7P": "GBP",
    "A39IBJ37TRP1C6": "AUD",
}
MARKETPLACE_AD_CURRENCY = MARKETPLACE_CURRENCY   # alias for clarity in ad-load

# COGS workbook sheet name per marketplace.
MARKETPLACE_TO_SHEET: dict[str, str] = {
    "ATVPDKIKX0DER": "US",
    "A2EUQ1WTGCTBG2": "CA",
    "A1F83G8C2ARO7P": "UK",
    "A39IBJ37TRP1C6": "AU",
}

# Our marketplace_id → sp_api Marketplaces enum. The library uses "GB" for the
# UK marketplace_id (A1F83G8C2ARO7P) as the canonical name; `.UK` is an alias.
MARKETPLACE_TO_ENUM: dict[str, Marketplaces] = {
    "ATVPDKIKX0DER": Marketplaces.US,
    "A2EUQ1WTGCTBG2": Marketplaces.CA,
    "A1F83G8C2ARO7P": Marketplaces.GB,
    "A39IBJ37TRP1C6": Marketplaces.AU,
}

# Refresh tokens are region-scoped (NA covers US+CA, EU covers UK, FE covers AU).
MARKETPLACE_TO_REFRESH_ENV: dict[str, str] = {
    "ATVPDKIKX0DER": "AMAZON_SP_REFRESH_TOKEN_NA",
    "A2EUQ1WTGCTBG2": "AMAZON_SP_REFRESH_TOKEN_NA",
    "A1F83G8C2ARO7P": "AMAZON_SP_REFRESH_TOKEN_EU",
    "A39IBJ37TRP1C6": "AMAZON_SP_REFRESH_TOKEN_FE",
}

# Per-marketplace refund-COGS basis (attribution of refund_qty × cog).
# Empirically tested per rollout task — US and UK win with purchase-date basis,
# CA prefers postedDate (Σ|Δ| $2596.90 posted vs $3090.23 purchase).
# Refund-dollar attribution (not COGS) is always postedDate in every market
# tested, so no per-marketplace switch needed there.
MARKETPLACE_REFUND_COGS_BASIS: dict[str, str] = {
    "ATVPDKIKX0DER": "purchase",   # US
    "A2EUQ1WTGCTBG2": "posted",    # CA — differs from US
    "A1F83G8C2ARO7P": "purchase",  # UK
    "A39IBJ37TRP1C6": "purchase",  # AU — assumed until AU Sellerise target lands
}

# Per-marketplace cog *source* override — when set, cog lookups for the key
# marketplace fall back to the target marketplace's `cogs_per_sku` values.
#
# Why CA→US: the CA sheet of `COGS_Magical_Butter_1.xlsx` has each SKU's cog
# set to `US_cog × 1.35` — a mechanically derived FX-like markup, not real
# CA-sourced per-unit costs. Empirically this produces a **same-signed
# +$258-$632/month cog residual** vs Sellerise. Overriding to US cog values
# (matching the UK sheet's approach, which uses US-parity values) collapses
# the residual to **mixed-sign, magnitude comparable to UK's small drift band**
# (Σ|Δ| 2597 → 909, mean/mo 433 → 152, all-negative → mixed-sign).
#
# This is a **provisional override** pending real CA-sourced per-unit cost
# data landing in the CA sheet. When it does, remove this entry.
MARKETPLACE_COG_SOURCE_OVERRIDE: dict[str, str] = {
    "A2EUQ1WTGCTBG2": "ATVPDKIKX0DER",  # CA cog looks up in US table
}


def cog_source_marketplace(marketplace_id: str) -> str:
    """Marketplace_id whose `cogs_per_sku` rows we should join for cog lookup.

    Falls back to the marketplace itself when no override is set.
    """
    return MARKETPLACE_COG_SOURCE_OVERRIDE.get(marketplace_id, marketplace_id)

# Backfill start (per project decision — matches the Sellerise sheet).
BACKFILL_START_ISO = "2026-01-01T00:00:00Z"


def credentials_for(marketplace_id: str) -> dict[str, str]:
    """Return a credentials dict in the shape python-amazon-sp-api expects.

    Reads our AMAZON_SP_* env vars and re-keys them to lwa_app_id / lwa_client_secret
    / refresh_token so the library's FromCodeCredentialProvider picks them up.
    """
    refresh_env = MARKETPLACE_TO_REFRESH_ENV[marketplace_id]
    return {
        "lwa_app_id": _require_env("AMAZON_SP_CLIENT_ID"),
        "lwa_client_secret": _require_env("AMAZON_SP_CLIENT_SECRET"),
        "refresh_token": _require_env(refresh_env),
    }


def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Missing required env var: {name}")
    return val
