"""Static config: marketplace metadata + credential mapping for python-amazon-sp-api.

Regional routing (host + AWS region) is handled by the library's `Marketplaces`
enum — we just map our marketplace_id string to the corresponding enum member.

Refresh tokens are grouped per region (one token covers every marketplace in
that region), so we keep a small marketplace_id → refresh_token_env mapping.
"""

from __future__ import annotations

import os
import pathlib
from decimal import Decimal

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

# Currency of the COGS column in each workbook sheet. This is NOT inferrable
# from the marketplace: the AU sheet's retail column is AUD while its COGS
# column is USD, and the CA sheet's COGS column is CAD (= US x 1.35). Verified
# arithmetically in `reference/data/au_sellerboard_reconcile.md`:
#
#   AU: GMAKER-3 cog 30.99 vs US 30.76 (ratio 1.007). If the sheet were AUD the
#       ratio would be ~1.49. Corroborated by Sellerboard's USD `productCosts`
#       dividing our USD-basis cog at ~1.05, not ~1.50.
#   CA: every SKU is exactly US x 1.350 (a CAD markup), so the sheet is CAD.
#       Unused in practice - MARKETPLACE_COG_SOURCE_OVERRIDE redirects CA to
#       the US (USD) sheet, which is what Sellerise CA's `cog` actually matches.
#   UK: US-parity values (GMAKER-3 30.94 vs 30.76), and Sellerise UK's `cog`
#       matches the sheet, so both sides are the same denomination.
#
# A marketplace whose cog currency != its transaction currency needs explicit
# FX handling at the point of use. Never infer sheet currency from the
# marketplace again - that assumption is what MARKETPLACE_COG_SOURCE_OVERRIDE
# was originally (mis)diagnosed as fixing.
MARKETPLACE_COG_CURRENCY: dict[str, str] = {
    "ATVPDKIKX0DER": "USD",   # US sheet, US pipeline - no conversion
    "A2EUQ1WTGCTBG2": "CAD",  # CA sheet is CAD, but overridden to the US sheet
    "A1F83G8C2ARO7P": "USD",  # UK sheet holds US-parity values
    "A39IBJ37TRP1C6": "USD",  # AU sheet is USD while AU transactions are AUD
}

# COGS workbook sheet name per marketplace.
MARKETPLACE_TO_SHEET: dict[str, str] = {
    "ATVPDKIKX0DER": "US",
    "A2EUQ1WTGCTBG2": "CA",
    "A1F83G8C2ARO7P": "UK",
    "A39IBJ37TRP1C6": "AU",
}


def cog_currency(marketplace_id: str) -> str:
    """Currency of the cog values actually used for `marketplace_id`.

    Resolves MARKETPLACE_COG_SOURCE_OVERRIDE first: CA joins the US sheet, so
    CA's effective cog currency is USD (the US sheet's), not CAD (its own).
    """
    return MARKETPLACE_COG_CURRENCY[cog_source_marketplace(marketplace_id)]


def cog_needs_fx(marketplace_id: str) -> bool:
    """True when a marketplace's effective cog currency differs from the
    currency its transactions are denominated in, so cog must be converted
    before it can be combined with transaction-derived buckets."""
    return cog_currency(marketplace_id) != MARKETPLACE_CURRENCY[marketplace_id]

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
    # AU: UNTESTED. The posted-vs-purchase test needs `order_purchase_date`,
    # which has 0 AU rows (no getOrders backfill has run for AU). Refunds
    # therefore fall back to postedDate regardless of this value.
    "A39IBJ37TRP1C6": "purchase",
}

# Guard values for the AU cog double-conversion trap. The AU sheet is USD while
# AU transactions are AUD, so `cog_needs_fx("A39IBJ37TRP1C6")` is True and the
# cog must be converted exactly once. GMAKER-3 is the canary: US sheet 30.76,
# AU sheet 30.99, so at an implied rate near 0.70 the AUD cog must land near 44.
# The two failure modes both produce plausible-looking numbers:
#   ~21 AUD  = 30.99 x 0.70  (converted the wrong way: USD sheet read as AUD)
#   ~63 AUD  = 30.99 / 0.70 / 0.70  (converted twice)
COG_FX_GUARD_SKU = "GMAKER-3"
COG_FX_GUARD_AUD_RANGE = (Decimal("40"), Decimal("50"))

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
