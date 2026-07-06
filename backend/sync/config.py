"""Static config: marketplace → region → SP-API host + env var name."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

# COGS workbook path (relative to repo root).
COGS_XLSX = _REPO_ROOT / "reference" / "data" / "COGS_Magical_Butter_1.xlsx"


@dataclass(frozen=True)
class RegionConfig:
    name: str
    host: str
    refresh_token_env: str
    marketplace_ids: tuple[str, ...]


NA = RegionConfig(
    name="NA",
    host="https://sellingpartnerapi-na.amazon.com",
    refresh_token_env="AMAZON_SP_REFRESH_TOKEN_NA",
    marketplace_ids=("ATVPDKIKX0DER", "A2EUQ1WTGCTBG2"),  # US, CA
)
EU = RegionConfig(
    name="EU",
    host="https://sellingpartnerapi-eu.amazon.com",
    refresh_token_env="AMAZON_SP_REFRESH_TOKEN_EU",
    marketplace_ids=("A1F83G8C2ARO7P",),  # UK
)
FE = RegionConfig(
    name="FE",
    host="https://sellingpartnerapi-fe.amazon.com",
    refresh_token_env="AMAZON_SP_REFRESH_TOKEN_FE",
    marketplace_ids=("A39IBJ37TRP1C6",),  # AU
)

REGIONS: tuple[RegionConfig, ...] = (NA, EU, FE)

MARKETPLACE_TO_REGION: dict[str, RegionConfig] = {
    mid: region for region in REGIONS for mid in region.marketplace_ids
}

# Marketplace → native currency (per the "no FX conversion" decision).
MARKETPLACE_CURRENCY: dict[str, str] = {
    "ATVPDKIKX0DER": "USD",
    "A2EUQ1WTGCTBG2": "CAD",
    "A1F83G8C2ARO7P": "GBP",
    "A39IBJ37TRP1C6": "AUD",
}

US_MARKETPLACE_ID = "ATVPDKIKX0DER"

MARKETPLACE_ALIASES: dict[str, str] = {
    "US": "ATVPDKIKX0DER",
    "CA": "A2EUQ1WTGCTBG2",
    "UK": "A1F83G8C2ARO7P",
    "AU": "A39IBJ37TRP1C6",
}

# COGS workbook sheet name per marketplace.
MARKETPLACE_TO_SHEET: dict[str, str] = {
    "ATVPDKIKX0DER": "US",
    "A2EUQ1WTGCTBG2": "CA",
    "A1F83G8C2ARO7P": "UK",
    "A39IBJ37TRP1C6": "AU",
}

# Backfill start (per project decision — matches the Sellerise sheet).
BACKFILL_START_ISO = "2026-01-01T00:00:00Z"
