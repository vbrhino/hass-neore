"""Sensors: the 13 frozen hass-neore sensors, further map registers, and gateway estimates (/api/derived)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import LEGACY, LegacySensor
from .coordinator import NeoreConfigEntry, NeoreCoordinator
from .entity import NeoreEntity, NeoreRegisterEntity, display_name

PARALLEL_UPDATES = 0

# Unit -> device class for registers outside the legacy table; anything else gets none.
_UNIT_DEVICE_CLASS = {
    "°C": SensorDeviceClass.TEMPERATURE,
    "kW": SensorDeviceClass.POWER,
    "W": SensorDeviceClass.POWER,
}

# /api/derived key -> (unique_id, name, unit, device_class)
DERIVED: dict[str, tuple[str, str, str | None, SensorDeviceClass | None]] = {
    "electric_kw": ("neore_derived_electric_kw", "Neore Electric Power Estimate", UnitOfPower.KILO_WATT,
                    SensorDeviceClass.POWER),
    "cop": ("neore_derived_cop", "Neore COP Estimate", None, None),
}


def _unique_id(register: dict[str, Any]) -> str:
    return register.get("unique_id") or f"neore_{register['id']}"


async def async_setup_entry(
    hass: HomeAssistant, entry: NeoreConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    runtime = entry.runtime_data
    coordinator = runtime.coordinator
    by_uid = {_unique_id(r): r for r in runtime.registers}

    entities: list[SensorEntity] = []
    legacy_ids: set[str] = set()
    for uid, legacy in LEGACY.items():
        reg = by_uid.get(uid) or {}
        register_id = reg.get("id") or legacy.register_id
        legacy_ids.add(register_id)
        entities.append(LegacyNeoreSensor(coordinator, uid, legacy, register_id, bool(reg.get("deprecated"))))
    taken = set(LEGACY) | {d[0] for d in DERIVED.values()}
    for uid, reg in by_uid.items():
        if uid in taken or reg["id"] in legacy_ids or reg.get("access") == "rw":
            continue
        entities.append(RegisterSensor(coordinator, uid, reg))
    if coordinator.data and coordinator.data.derived is not None:
        entities.extend(DerivedSensor(coordinator, key, *spec) for key, spec in DERIVED.items())
    async_add_entities(entities)


class _StateSensor(NeoreRegisterEntity, SensorEntity):
    @property
    def native_value(self) -> Any:
        return self._reading().get("value")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"quality": self._reading().get("quality")}


class LegacyNeoreSensor(_StateSensor):
    """Identity (unique_id, name, unit, classes) comes from LEGACY only, never from the gateway map."""

    def __init__(self, coordinator: NeoreCoordinator, unique_id: str, legacy: LegacySensor, register_id: str,
                 deprecated: bool) -> None:
        super().__init__(coordinator, unique_id, legacy.name)
        self._register_id = register_id
        self._attr_native_unit_of_measurement = legacy.unit
        self._attr_device_class = legacy.device_class
        self._attr_state_class = legacy.state_class
        self._attr_suggested_display_precision = legacy.precision
        # Applies to new registry entries only; an existing entity keeps its enabled/disabled state.
        self._attr_entity_registry_enabled_default = not deprecated


class RegisterSensor(_StateSensor):
    def __init__(self, coordinator: NeoreCoordinator, unique_id: str, register: dict[str, Any]) -> None:
        super().__init__(coordinator, unique_id, display_name(register))
        self._register_id = register["id"]
        unit = register.get("unit")
        numeric = register.get("type") in ("real", "int")
        self._attr_native_unit_of_measurement = unit if numeric else None
        self._attr_device_class = _UNIT_DEVICE_CLASS.get(unit) if numeric else None
        self._attr_state_class = SensorStateClass.MEASUREMENT if numeric else None
        self._attr_entity_registry_enabled_default = not register.get("deprecated")

    @property
    def native_value(self) -> Any:
        value = super().native_value
        return str(value).lower() if isinstance(value, bool) else value


class DerivedSensor(NeoreEntity, SensorEntity):
    """A gateway estimate with its band and source label; label `onbekend` -> state unknown."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: NeoreCoordinator, key: str, unique_id: str, name: str, unit: str | None,
                 device_class: SensorDeviceClass | None) -> None:
        super().__init__(coordinator, unique_id, name)
        self._key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class

    def _item(self) -> dict[str, Any]:
        derived = self.coordinator.data.derived or {}
        item = derived.get(self._key)
        return item if isinstance(item, dict) else {}

    @property
    def native_value(self) -> float | None:
        item = self._item()
        if item.get("label") in (None, "onbekend", "unknown"):
            return None
        return item.get("value")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        item = self._item()
        return {k: item.get(k) for k in ("low", "high", "label", "basis")}
