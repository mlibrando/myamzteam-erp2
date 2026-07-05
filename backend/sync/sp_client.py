"""SP-API HTTP client: LWA refresh + rate-limited GET with retry.

SP-API auth is LWA bearer-only. No AWS SigV4 signing required.
Reference: developer-docs.amazon.com/sp-api/docs/connecting-to-the-selling-partner-api.

Rate limiting is per-operation on the server side, but a simple token bucket at
0.5 req/sec + burst 10 (the listTransactions limit) is safe as a global ceiling
for this client's callers.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

from .config import REGIONS, RegionConfig

log = logging.getLogger(__name__)

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
USER_AGENT = "MyAmzTeamERP/0.1 (Language=Python)"


class SPAPIError(RuntimeError):
    def __init__(self, status: int, body: str):
        super().__init__(f"SP-API {status}: {body[:500]}")
        self.status = status
        self.body = body


class SPClient:
    """One instance per region. Sync API — the sync module runs sequentially."""

    def __init__(
        self,
        region: RegionConfig,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        rps: float = 0.5,
        burst: int = 10,
    ) -> None:
        self.region = region
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._rps = rps
        self._burst = burst
        self._http = httpx.Client(timeout=60.0)
        self._access_token: str | None = None
        self._access_token_expires_at: float = 0.0
        self._bucket_tokens: float = float(burst)
        self._bucket_last_refill: float = time.monotonic()

    # ---- lifecycle ----
    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "SPClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # ---- factory ----
    @classmethod
    def for_marketplace(cls, marketplace_id: str) -> "SPClient":
        from .config import MARKETPLACE_TO_REGION

        region = MARKETPLACE_TO_REGION[marketplace_id]
        return cls.for_region(region)

    @classmethod
    def for_region(cls, region: RegionConfig) -> "SPClient":
        client_id = _require_env("AMAZON_SP_CLIENT_ID")
        client_secret = _require_env("AMAZON_SP_CLIENT_SECRET")
        refresh_token = _require_env(region.refresh_token_env)
        return cls(region, client_id, client_secret, refresh_token)

    # ---- auth ----
    def _access_token_valid(self) -> bool:
        return self._access_token is not None and time.time() < self._access_token_expires_at

    def _refresh_access_token(self) -> None:
        log.debug("Refreshing LWA access token (region=%s)", self.region.name)
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
            raise SPAPIError(r.status_code, r.text)
        body = r.json()
        self._access_token = body["access_token"]
        # Refresh 60s before actual expiry.
        self._access_token_expires_at = time.time() + int(body.get("expires_in", 3600)) - 60

    def _get_access_token(self) -> str:
        if not self._access_token_valid():
            self._refresh_access_token()
        assert self._access_token is not None
        return self._access_token

    # ---- rate limit (token bucket) ----
    def _wait_for_capacity(self) -> None:
        now = time.monotonic()
        elapsed = now - self._bucket_last_refill
        self._bucket_tokens = min(float(self._burst), self._bucket_tokens + elapsed * self._rps)
        self._bucket_last_refill = now
        if self._bucket_tokens < 1.0:
            sleep_s = (1.0 - self._bucket_tokens) / self._rps
            time.sleep(sleep_s)
            self._bucket_tokens = 0.0
            self._bucket_last_refill = time.monotonic()
        else:
            self._bucket_tokens -= 1.0

    # ---- GET ----
    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.region.host}{path}"
        backoff = 1.0
        for attempt in range(6):
            self._wait_for_capacity()
            token = self._get_access_token()
            r = self._http.get(
                url,
                params=params,
                headers={
                    "x-amz-access-token": token,
                    "user-agent": USER_AGENT,
                    "accept": "application/json",
                },
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401:
                # Token could have been invalidated; force refresh once and retry immediately.
                log.warning("SP-API 401 — forcing token refresh")
                self._access_token = None
                self._access_token_expires_at = 0.0
                if attempt == 0:
                    continue
            if r.status_code == 429 or r.status_code >= 500:
                log.warning("SP-API %s on %s (attempt %d); backing off %.1fs", r.status_code, path, attempt + 1, backoff)
                time.sleep(backoff)
                backoff = min(60.0, backoff * 2)
                continue
            raise SPAPIError(r.status_code, r.text)
        raise SPAPIError(-1, f"exhausted retries for GET {path}")


def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Missing required env var: {name}")
    return val
