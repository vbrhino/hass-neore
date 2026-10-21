"""Thin REST client for neore-gateway. The gateway is the only PLC client; this never talks to the PLC."""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from .const import REQUEST_TIMEOUT


# Not a register id in any map: the token check's dry run is refused (not_allowed) after the auth check.
TOKEN_PROBE_REGISTER = "__neore_token_check__"


class GatewayError(Exception):
    """Gateway unreachable or answered with something unusable."""


class GatewayAuthError(GatewayError):
    """POST refused with 401: API token missing or wrong."""


class GatewayWriteUnknown(GatewayError):
    """The POST may have reached the gateway (timeout, dropped connection, unreadable answer): outcome unknown."""


class GatewayWriteRefused(GatewayError):
    """The WriteGuard refused or failed a write; `result` is the gateway's result code."""

    def __init__(self, result: str, detail: str | None, status: int) -> None:
        super().__init__(f"{result}: {detail}" if detail else result)
        self.result = result
        self.detail = detail
        self.status = status


def normalize_url(url: str) -> str:
    return url.strip().rstrip("/")


class GatewayClient:
    def __init__(self, session: aiohttp.ClientSession, url: str, token: str | None = None) -> None:
        self._session = session
        self.url = normalize_url(url)
        self._token = token or None

    @property
    def has_token(self) -> bool:
        return self._token is not None

    async def _get(self, path: str, *, allow_404: bool = False) -> Any:
        try:
            async with self._session.get(
                f"{self.url}{path}", timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if allow_404 and resp.status == 404:
                    return None
                if resp.status != 200:
                    raise GatewayError(f"GET {path}: HTTP {resp.status}")
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            raise GatewayError(f"GET {path}: {err!r}") from err

    async def health(self) -> dict[str, Any]:
        return await self._get("/api/health")

    async def state(self) -> dict[str, Any]:
        return await self._get("/api/state")

    async def registers(self) -> dict[str, Any]:
        return await self._get("/api/registers")

    async def derived(self) -> dict[str, Any] | None:
        """Phase-2 endpoint; None when the gateway does not serve it (404)."""
        return await self._get("/api/derived", allow_404=True)

    async def boost(self) -> dict[str, Any] | None:
        """The gateway's price-boost status; None when the gateway does not serve it (404)."""
        return await self._get("/api/boost", allow_404=True)

    async def check_token(self) -> None:
        """Raise GatewayAuthError when the gateway rejects the token. A dry run on a register that does not exist:
        the auth check runs first, then the WriteGuard refuses; nothing is written or audited."""
        if not self._token:
            raise GatewayAuthError("no API token configured")
        body = {"register": TOKEN_PROBE_REGISTER, "value": 0, "reason": "token check", "actor": "home-assistant"}
        try:
            async with self._session.post(
                f"{self.url}/api/write",
                params={"dry_run": "1"},
                json=body,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                status = resp.status
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise GatewayError(f"POST /api/write?dry_run=1: {err!r}") from err
        if status == 401:
            raise GatewayAuthError("unauthorized")

    async def write(self, register: str, value: Any, reason: str) -> dict[str, Any]:
        """POST /api/write. Returns the WriteResult on 200; raises on anything else."""
        if not self._token:
            raise GatewayAuthError("no API token configured")
        body = {"register": register, "value": value, "reason": reason, "actor": "home-assistant"}
        try:
            async with self._session.post(
                f"{self.url}/api/write",
                json=body,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                data = await resp.json(content_type=None)
                status = resp.status
        except aiohttp.ClientConnectorError as err:  # no connection: nothing was sent
            raise GatewayError(f"POST /api/write: {err!r}") from err
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            raise GatewayWriteUnknown(f"POST /api/write: {err!r}") from err
        if status == 401:
            raise GatewayAuthError((data or {}).get("detail") or "unauthorized")
        if not isinstance(data, dict):
            raise GatewayWriteUnknown(f"POST /api/write: HTTP {status}")
        if status != 200:
            raise GatewayWriteRefused(str(data.get("result") or data.get("error") or status), data.get("detail"), status)
        return data
