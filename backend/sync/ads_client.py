"""Amazon Ads API v1 client — LWA auth + reporting flow.

Handles the LWA refresh-token → access-token exchange and provides simple
`request` helpers for the ads-v1 reporting endpoints (`/adsApi/v1/...`) and
account list (`/adsAccounts/list`).

The `Amazon-*-ClientId` header name is inconsistent in Amazon's docs — some
pages say `Amazon-Ads-ClientId`, others `Amazon-Advertising-API-ClientId`.
We resolve empirically: try both on `/adsAccounts/list` and record which works.
The winner is cached on the client instance and reused.

Reference: reference/ads-v1/*.md, especially:
- reporting-quickstart.md (POST /adsApi/v1/create/reports and retrieve)
- retrieving-accounts.md (POST /adsAccounts/list)
- endpoints-regional-hosts.md (regional hosts + ClientId ambiguity)
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

log = logging.getLogger(__name__)

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"

# Region → host. US is NA.
ADS_HOSTS = {
    "NA": "https://advertising-api.amazon.com",
    "EU": "https://advertising-api-eu.amazon.com",
    "FE": "https://advertising-api-fe.amazon.com",
}

# Env vars per region — refresh-token per region, single client_id/secret.
ADS_REFRESH_ENV = {
    "NA": "AMAZON_ADS_REFRESH_TOKEN_NA",
    "EU": "AMAZON_ADS_REFRESH_TOKEN_EU",
    "FE": "AMAZON_ADS_REFRESH_TOKEN_FE",
}

CLIENT_ID_HEADER_CANDIDATES = ("Amazon-Ads-ClientId", "Amazon-Advertising-API-ClientId")


class AdsAPIError(RuntimeError):
    def __init__(self, status: int, body: str, headers: dict | None = None):
        super().__init__(f"Ads API {status}: {body[:500]}")
        self.status = status
        self.body = body
        self.headers = dict(headers or {})


class AdsClient:
    """One instance per region (NA covers US/CA/MX/BR)."""

    def __init__(self, region: str = "NA") -> None:
        self.region = region
        self.host = ADS_HOSTS[region]
        self._client_id = _require_env("AMAZON_ADS_CLIENT_ID")
        self._client_secret = _require_env("AMAZON_ADS_CLIENT_SECRET")
        self._refresh_token = _require_env(ADS_REFRESH_ENV[region])
        self._http = httpx.Client(timeout=60.0)
        self._access_token: str | None = None
        self._access_token_expires_at: float = 0.0
        # Resolved by probe on first `/adsAccounts/list` call.
        self._client_id_header: str | None = None

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "AdsClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # ── auth ────────────────────────────────────────────────────────────────
    def _token_valid(self) -> bool:
        return self._access_token is not None and time.time() < self._access_token_expires_at

    def _refresh_access_token(self) -> None:
        log.debug("Refreshing Ads-API access token (region=%s)", self.region)
        r = self._http.post(
            LWA_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
        )
        if r.status_code != 200:
            raise AdsAPIError(r.status_code, r.text)
        body = r.json()
        self._access_token = body["access_token"]
        self._access_token_expires_at = time.time() + int(body.get("expires_in", 3600)) - 60

    def access_token(self) -> str:
        if not self._token_valid():
            self._refresh_access_token()
        assert self._access_token is not None
        return self._access_token

    # ── ClientId header probe ───────────────────────────────────────────────
    def resolve_client_id_header(self) -> str:
        """Try each candidate header name against /adsAccounts/list.

        Returns the header name that produced a 2xx. Caches the winner.
        """
        if self._client_id_header:
            return self._client_id_header

        url = f"{self.host}/adsAccounts/list"
        for header in CLIENT_ID_HEADER_CANDIDATES:
            headers = {
                "Authorization": f"Bearer {self.access_token()}",
                header: self._client_id,
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            r = self._http.post(url, headers=headers)
            log.info("ClientId probe: %-40s → %d %s", header, r.status_code, r.reason_phrase)
            if r.is_success:
                self._client_id_header = header
                return header
        raise AdsAPIError(
            -1,
            f"Neither {CLIENT_ID_HEADER_CANDIDATES} was accepted by /adsAccounts/list",
        )

    # ── HTTP helpers ────────────────────────────────────────────────────────
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token()}",
            self.resolve_client_id_header(): self._client_id,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def post(self, path: str, json: dict | None = None) -> dict:
        url = f"{self.host}{path}"
        r = self._http.post(url, headers=self._headers(), json=json)
        if not r.is_success:
            raise AdsAPIError(r.status_code, r.text, dict(r.headers))
        return r.json()

    def get(self, path: str) -> dict:
        url = f"{self.host}{path}"
        r = self._http.get(url, headers=self._headers())
        if not r.is_success:
            raise AdsAPIError(r.status_code, r.text, dict(r.headers))
        return r.json()

    def download(self, url: str) -> bytes:
        """Download from a presigned S3 URL (no auth headers)."""
        r = self._http.get(url, follow_redirects=True)
        if not r.is_success:
            raise AdsAPIError(r.status_code, r.text[:500])
        return r.content


def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Missing required env var: {name}")
    return val
