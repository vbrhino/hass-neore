"""Sensors: the 13 frozen hass-neore sensors, further map registers, gateway estimates (/api/derived) and the
gateway's price-boost status (/api/boost)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LEGACY, LegacySensor
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

BOOST_UNIQUE_ID = "neore_boost"


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
    taken = set(LEGACY) | {d[0] for d in DERIVED.values()} | {BOOST_UNIQUE_ID}
    for uid, reg in by_uid.items():
        if uid in taken or reg["id"] in legacy_ids or reg.get("access") == "rw":
            continue
        entities.append(RegisterSensor(coordinator, uid, reg))
    if coordinator.data and coordinator.data.derived is not None:
        entities.extend(DerivedSensor(coordinator, key, *spec) for key, spec in DERIVED.items())
    # Created when the gateway serves /api/boost, or kept when it existed before (a failed first fetch).
    if (coordinator.data and coordinator.data.boost is not None) or er.async_get(hass).async_get_entity_id(
            "sensor", DOMAIN, BOOST_UNIQUE_ID):
        entities.append(BoostSensor(coordinator))
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


def _local_iso(ts: Any) -> str | None:
    if isinstance(ts, bool) or not isinstance(ts, (int, float)):
        return None
    return dt_util.as_local(dt_util.utc_from_timestamp(ts)).isoformat()


class BoostSensor(NeoreEntity, SensorEntity):
    """The gateway's price boost: state disabled/no_prices/idle/planned/active/aborted/killswitch, plan as attributes.
    Unavailable while the gateway serves no boost status; does not follow the PLC status (the gateway's own state)."""

    _attr_icon = "mdi:rocket-launch-outline"

    def __init__(self, coordinator: NeoreCoordinator) -> None:
        super().__init__(coordinator, BOOST_UNIQUE_ID, "Neore Boost")

    def _boost(self) -> dict[str, Any]:
        return self.coordinator.data.boost or {}

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data.boost is not None

    @property
    def native_value(self) -> str | None:
        state = self._boost().get("state")
        return str(state) if state is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        b = self._boost()
        plan = b.get("plan") if isinstance(b.get("plan"), dict) else {}
        last = b.get("last_action") if isinstance(b.get("last_action"), dict) else {}
        return {
            "enabled": b.get("enabled"),
            "mode": b.get("mode"),
            "plan_start": _local_iso(plan.get("start")),
            "plan_end": _local_iso(plan.get("end")),
            "avg_price": plan.get("avg_price"),
            "ref_avg_price": plan.get("ref_avg_price"),
            "baseline": b.get("baseline"),
            "boost_value": b.get("boost_value"),
            "skip_reasons": list(b.get("skip_reasons") or []),
            "last_action_ts": _local_iso(last.get("ts")),
            "last_action_result": last.get("result"),
            "last_action_value": last.get("value"),
        }
