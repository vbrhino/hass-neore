"""Boolean rw registers."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import NeoreConfigEntry
from .writable import NeoreWritable, writable_registers

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant, entry: NeoreConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    rt = entry.runtime_data
    async_add_entities(
        NeoreSwitch(rt.coordinator, rt.client, r) for r in writable_registers(entry, lambda r: r.get("type") == "bool")
    )


class NeoreSwitch(NeoreWritable, SwitchEntity):
    @property
    def is_on(self) -> bool | None:
        value = self.current
        return value if isinstance(value, bool) else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_write(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_write(False)
