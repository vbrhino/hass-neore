"""Numeric rw registers (type real/int)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import NeoreConfigEntry, NeoreCoordinator
from .gateway import GatewayClient
from .writable import NeoreWritable, check_step, writable_registers

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant, entry: NeoreConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    rt = entry.runtime_data
    async_add_entities(
        NeoreNumber(rt.coordinator, rt.client, r)
        for r in writable_registers(entry, lambda r: r.get("type") in ("real", "int"))
    )


class NeoreNumber(NeoreWritable, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: NeoreCoordinator, client: GatewayClient, register: dict[str, Any]) -> None:
        super().__init__(coordinator, client, register)
        self._attr_native_unit_of_measurement = register.get("unit")
        if register.get("min") is not None:
            self._attr_native_min_value = float(register["min"])
        if register.get("max") is not None:
            self._attr_native_max_value = float(register["max"])
        self._attr_native_step = 1.0 if register.get("type") == "int" else 0.1

    @property
    def native_value(self) -> float | None:
        value = self.current
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    async def async_set_native_value(self, value: float) -> None:
        check_step(self._register, self.current, value)
        await self._async_write(int(value) if self._register.get("type") == "int" else value)
