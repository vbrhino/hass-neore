"""Diagnostics: entry (token redacted), gateway health, map and last poll."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_TOKEN
from .coordinator import NeoreConfigEntry
from .gateway import GatewayError

TO_REDACT = {CONF_TOKEN}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: NeoreConfigEntry) -> dict[str, Any]:
    rt = entry.runtime_data
    coordinator = rt.coordinator
    try:
        health: Any = await rt.client.health()
    except GatewayError as err:
        health = {"error": str(err)}
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "has_token": rt.client.has_token,
        "gateway_health": health,
        "map_version": rt.map_version,
        "registers": rt.registers,
        "failed_polls": coordinator.failed_polls,
        "last_error": coordinator.last_error,
        "last_update_success": coordinator.last_update_success,
        "data": asdict(coordinator.data) if coordinator.data else None,
    }
