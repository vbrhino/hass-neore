"""Constants for the Neore integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

DOMAIN = "neore"

CONF_URL = "url"
CONF_TOKEN = "token"

DEFAULT_URL = "http://127.0.0.1:8470"
SCAN_INTERVAL = timedelta(seconds=30)
REQUEST_TIMEOUT = 10
# Entities go unavailable and a repair issue opens after this many failed polls in a row.
# A repair issue also opens after this many polls in a row with the PLC offline.
MAX_FAILED_POLLS = 3

ISSUE_YAML = "deprecated_yaml"
ISSUE_UNREACHABLE = "gateway_unreachable"
ISSUE_PLC_OFFLINE = "plc_offline"

MANUFACTURER = "NeoRé"
DEVICE_NAME = "Neore"


@dataclass(frozen=True)
class LegacySensor:
    """A hass-neore sensor whose identity is frozen for history and long-term statistics."""

    register_id: str  # gateway register id in /api/state (fallback when /api/registers lacks the unique_id)
    name: str
    unit: str | None
    device_class: SensorDeviceClass | None
    state_class: SensorStateClass | None
    precision: int


# unique_id -> frozen identity. Never derived from the gateway map: a map change can not rename these.
# unique_id = "neore_" + PLC field name, as hass-neore 0.2.0 created them.
LEGACY: dict[str, LegacySensor] = {
    "neore___R7195_REAL_.1f": LegacySensor(
        "object_temperature", "Neore Object Temperature", "°C",
        SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, 1),
    "neore___R7079_REAL_.0f": LegacySensor(
        "outdoor_temperature", "Neore Outdoor Temperature", "°C",
        SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, 1),
    "neore___R15173_REAL_.0f": LegacySensor(
        "circulation_pump_percent", "Neore Circulation Percent", "%",
        None, SensorStateClass.MEASUREMENT, 0),
    "neore___R7070_REAL_.0f": LegacySensor(
        "outdoor_unit_percent", "Neore Outdoor Unit Circulation Percent", "%",
        None, SensorStateClass.MEASUREMENT, 0),
    "neore___R15104_REAL_.1f": LegacySensor(
        "supply_temperature", "Neore Output Temperature", "°C",
        SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, 1),
    "neore___R7096_REAL_.1f": LegacySensor(
        "return_temperature", "Neore Input Temperature", "°C",
        SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, 1),
    "neore___R7312_REAL_.0f": LegacySensor(
        "required_temperature", "Neore Required Temperature", "°C",
        SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, 1),
    "neore___R7083_REAL_.1f": LegacySensor(
        "water_flow", "Neore Water Flow", "m³/h",
        SensorDeviceClass.VOLUME_FLOW_RATE, SensorStateClass.MEASUREMENT, 2),
    # Heat output, not electricity; name kept for continuity.
    "neore___R7087_REAL_.1f": LegacySensor(
        "heat_power", "Neore Actual Power Usage", "kW",
        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 2),
    # Cumulative heat, not electricity; feeds the Energy dashboard.
    "neore___R7091_REAL_.0f": LegacySensor(
        "heat_energy", "Neore Supplied Power", "kWh",
        SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, 1),
    # "Bar" is not an HA pressure unit, so no device class.
    "neore___R7297_REAL_.1f": LegacySensor(
        "water_pressure", "Neore Water Pressure", "Bar",
        None, SensorStateClass.MEASUREMENT, 1),
    "neore_temperature_delta": LegacySensor(
        "temperature_delta", "Neore Temperature Delta", "°C",
        None, SensorStateClass.MEASUREMENT, 1),
    "neore_cop": LegacySensor(
        "cop", "Neore COP", None,
        None, SensorStateClass.MEASUREMENT, 2),
}
