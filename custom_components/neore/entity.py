"""Shared entity base."""
from __future__ import annotations

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


def display_name(register: dict) -> str:
    """Name for a register outside the legacy table."""
    return "Neore " + str(register["id"]).replace("_", " ").capitalize()
