"""Enum rw registers. Needs `options` (raw value -> label) in /api/registers; without it the register is skipped."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import NeoreConfigEntry, NeoreCoordinator
from .gateway import GatewayClient
from .writable import NeoreWritable, writable_registers

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


def _has_options(register: dict[str, Any]) -> bool:
    if register.get("type") != "enum":
        return False
    if not isinstance(register.get("options"), dict) or not register["options"]:
        _LOGGER.warning("Enum register %s has no options in /api/registers; not exposed", register.get("id"))
        return False
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: NeoreConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    rt = entry.runtime_data
    async_add_entities(NeoreSelect(rt.coordinator, rt.client, r) for r in writable_registers(entry, _has_options))


class NeoreSelect(NeoreWritable, SelectEntity):
    def __init__(self, coordinator: NeoreCoordinator, client: GatewayClient, register: dict[str, Any]) -> None:
        super().__init__(coordinator, client, register)
        self._raw_by_label = {str(label): raw for raw, label in register["options"].items()}
        self._attr_options = list(self._raw_by_label)

    @property
    def current_option(self) -> str | None:
        value = self.current  # the gateway reports enums as their label
        return str(value) if value is not None and str(value) in self._raw_by_label else None

    async def async_select_option(self, option: str) -> None:
        await self._async_write(self._raw_by_label[option])
