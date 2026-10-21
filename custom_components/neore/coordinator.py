"""Polls /api/state (+ /api/derived, /api/boost) from neore-gateway."""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, ISSUE_PLC_OFFLINE, ISSUE_UNREACHABLE, MAX_FAILED_POLLS, SCAN_INTERVAL
from .gateway import GatewayClient, GatewayError

_LOGGER = logging.getLogger(__name__)


@dataclass
class NeoreData:
    state: dict[str, Any]
    derived: dict[str, Any] | None = None
    boost: dict[str, Any] | None = None

    def register(self, register_id: str) -> dict[str, Any] | None:
        return (self.state.get("registers") or {}).get(register_id)

    @property
    def plc_online(self) -> bool:
        """The gateway's PLC status; "offline" when its last good PLC poll is too old."""
        return self.state.get("plc") != "offline"

    def mode(self, register_id: str) -> str | None:
        return (self.state.get("modes") or {}).get(register_id)


@dataclass
class NeoreRuntime:
    client: GatewayClient
    coordinator: NeoreCoordinator
    registers: list[dict[str, Any]] = field(default_factory=list)
    map_version: int | None = None


type NeoreConfigEntry = ConfigEntry[NeoreRuntime]


class NeoreCoordinator(DataUpdateCoordinator[NeoreData]):
    """Keeps the last good data through short gateway outages.

    Entities stay available until more than MAX_FAILED_POLLS polls in a row fail; then they go
    unavailable and a repair issue opens. The first good poll closes it.
    A gateway that answers but reports the PLC offline for more than MAX_FAILED_POLLS polls opens a
    second repair issue; its entities are unavailable from the first such poll (NeoreEntity.available).
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: GatewayClient) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.client = client
        self.failed_polls = 0
        self.plc_offline_polls = 0
        self.last_error: str | None = None
        self.boost_failed_polls = 0

    async def _async_update_data(self) -> NeoreData:
        try:
            state = await self.client.state()
        except GatewayError as err:
            self.failed_polls += 1
            self.last_error = str(err)
            if self.failed_polls <= MAX_FAILED_POLLS and self.data is not None:
                _LOGGER.debug("Gateway poll %d failed, keeping last data: %s", self.failed_polls, err)
                return self.data
            if self.failed_polls == MAX_FAILED_POLLS + 1:
                ir.async_create_issue(
                    self.hass, DOMAIN, ISSUE_UNREACHABLE,
                    is_fixable=False, severity=ir.IssueSeverity.ERROR,
                    translation_key=ISSUE_UNREACHABLE,
                    translation_placeholders={"url": self.client.url, "error": str(err)},
                )
            raise UpdateFailed(f"neore-gateway unreachable at {self.client.url}: {err}") from err
        if self.failed_polls > MAX_FAILED_POLLS:
            ir.async_delete_issue(self.hass, DOMAIN, ISSUE_UNREACHABLE)
        self.failed_polls = 0
        self.last_error = None
        if not isinstance(state, dict):
            raise UpdateFailed("unexpected /api/state payload")
        self._track_plc(state.get("plc"))
        # Estimates are optional: a failing /api/derived keeps the previous block and never fails the poll.
        try:
            derived = await self.client.derived()
        except GatewayError as err:
            _LOGGER.debug("/api/derived failed, keeping previous estimates: %s", err)
            derived = self.data.derived if self.data else None
        return NeoreData(state=state, derived=derived if isinstance(derived, dict) else None, boost=await self._boost())

    async def _boost(self) -> dict[str, Any] | None:
        """/api/boost never fails the poll: a failure keeps the previous status for MAX_FAILED_POLLS polls, then
        None (boost entity unavailable). 404 (older gateway) is None at once."""
        try:
            boost = await self.client.boost()
        except GatewayError as err:
            self.boost_failed_polls += 1
            _LOGGER.debug("/api/boost failed (%d): %s", self.boost_failed_polls, err)
            previous = self.data.boost if self.data else None
            return previous if self.boost_failed_polls <= MAX_FAILED_POLLS else None
        self.boost_failed_polls = 0
        return boost if isinstance(boost, dict) else None

    def _track_plc(self, plc: Any) -> None:
        if plc != "offline":
            if self.plc_offline_polls > MAX_FAILED_POLLS:
                ir.async_delete_issue(self.hass, DOMAIN, ISSUE_PLC_OFFLINE)
            self.plc_offline_polls = 0
            return
        self.plc_offline_polls += 1
        if self.plc_offline_polls == MAX_FAILED_POLLS + 1:
            ir.async_create_issue(
                self.hass, DOMAIN, ISSUE_PLC_OFFLINE,
                is_fixable=False, severity=ir.IssueSeverity.ERROR,
                translation_key=ISSUE_PLC_OFFLINE,
                translation_placeholders={"url": self.client.url},
            )
