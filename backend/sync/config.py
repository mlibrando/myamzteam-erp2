"""Static config: marketplace → region → SP-API host + env var name."""

from __future__ import annotations

from dataclasses import dataclass


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

# Backfill start (per project decision — matches the Sellerise sheet).
BACKFILL_START_ISO = "2026-01-01T00:00:00Z"
