"""Shared entity base."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_NAME, DOMAIN, MANUFACTURER
from .coordinator import NeoreCoordinator


class NeoreEntity(CoordinatorEntity[NeoreCoordinator]):
    # Full names ("Neore Water Flow") so entity_ids stay sensor.neore_* as hass-neore created them.
    _attr_has_entity_name = False

    def __init__(self, coordinator: NeoreCoordinator, unique_id: str, name: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "gateway")},
            name=DEVICE_NAME,
            manufacturer=MANUFACTURER,
            model="neore-gateway",
            configuration_url=coordinator.client.url,
        )

    @property
    def available(self) -> bool:
        """Unavailable while the gateway reports the PLC offline: its values are no longer current."""
        return super().available and self.coordinator.data.plc_online


class NeoreRegisterEntity(NeoreEntity):
    """An entity backed by one register in /api/state; unavailable unless its quality is `good`."""

    _register_id: str

    def _reading(self) -> dict[str, Any]:
        return self.coordinator.data.register(self._register_id) or {}

    @property
    def available(self) -> bool:
        return super().available and self._reading().get("quality") == "good"


def display_name(register: dict) -> str:
    """Name for a register outside the legacy table."""
    return "Neore " + str(register["id"]).replace("_", " ").capitalize()
