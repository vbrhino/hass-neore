"""The 13 hass-neore sensors must keep unique_id, entity_id, name and unit (history + LTS)."""
from homeassistant.helpers import entity_registry as er

from conftest import load, make_entry, setup_entry

# unique_id -> (entity_id, friendly name, unit) as hass-neore 0.2.0 created them (entity_registry.json).
EXPECTED = {
    "neore___R7195_REAL_.1f": ("sensor.neore_object_temperature", "Neore Object Temperature", "°C"),
    "neore___R7079_REAL_.0f": ("sensor.neore_outdoor_temperature", "Neore Outdoor Temperature", "°C"),
    "neore___R15173_REAL_.0f": ("sensor.neore_circulation_percent", "Neore Circulation Percent", "%"),
    "neore___R7070_REAL_.0f": ("sensor.neore_outdoor_unit_circulation_percent",
                               "Neore Outdoor Unit Circulation Percent", "%"),
    "neore___R15104_REAL_.1f": ("sensor.neore_output_temperature", "Neore Output Temperature", "°C"),
    "neore___R7096_REAL_.1f": ("sensor.neore_input_temperature", "Neore Input Temperature", "°C"),
    "neore___R7312_REAL_.0f": ("sensor.neore_required_temperature", "Neore Required Temperature", "°C"),
    "neore___R7083_REAL_.1f": ("sensor.neore_water_flow", "Neore Water Flow", "m³/h"),
    "neore___R7087_REAL_.1f": ("sensor.neore_actual_power_usage", "Neore Actual Power Usage", "kW"),
    "neore___R7091_REAL_.0f": ("sensor.neore_supplied_power", "Neore Supplied Power", "kWh"),
    "neore___R7297_REAL_.1f": ("sensor.neore_water_pressure", "Neore Water Pressure", "Bar"),
    "neore_temperature_delta": ("sensor.neore_temperature_delta", "Neore Temperature Delta", "°C"),
    "neore_cop": ("sensor.neore_cop", "Neore COP", None),
}


async def test_existing_registry_rows_are_adopted(hass, gateway):
    """The owner's 13 YAML-era rows (no config entry, no device; tests/fixtures/legacy_registry.json, copied from
    the live entity registry) keep entity_id, enabled state and options, and are adopted by the config entry."""
    rows = load("legacy_registry.json")
    assert {r["unique_id"] for r in rows} == set(EXPECTED)
    reg = er.async_get(hass)
    for row in rows:
        entry = reg.async_get_or_create(
            "sensor", row["platform"], row["unique_id"],
            suggested_object_id=row["entity_id"].split(".", 1)[1],
            original_name=row["original_name"], has_entity_name=row["has_entity_name"],
        )
        assert entry.entity_id == row["entity_id"] and entry.config_entry_id is None
        for domain, options in row["options"].items():
            reg.async_update_entity_options(entry.entity_id, domain, options)
    entry = await setup_entry(hass, make_entry())

    for row in rows:
        entity_id = row["entity_id"]
        _, name, unit = EXPECTED[row["unique_id"]]
        assert reg.async_get_entity_id("sensor", "neore", row["unique_id"]) == entity_id
        adopted = reg.async_get(entity_id)
        assert adopted.config_entry_id == entry.entry_id
        assert adopted.disabled_by is None, entity_id  # neore_cop stays enabled for the existing install
        assert adopted.has_entity_name is False
        assert adopted.original_name == row["original_name"] == name
        for domain, options in row["options"].items():
            assert adopted.options[domain] == options, entity_id
        state = hass.states.get(entity_id)
        assert state is not None, entity_id
        assert state.attributes.get("friendly_name") == name
        assert state.attributes.get("unit_of_measurement") == unit


async def test_live_display_precision_matches_legacy_table():
    from custom_components.neore.const import LEGACY

    for row in load("legacy_registry.json"):
        assert LEGACY[row["unique_id"]].precision == row["options"]["sensor"]["suggested_display_precision"]


async def test_fresh_install_entity_ids(hass, gateway):
    await setup_entry(hass, make_entry())
    reg = er.async_get(hass)
    for uid, (entity_id, name, unit) in EXPECTED.items():
        assert reg.async_get_entity_id("sensor", "neore", uid) == entity_id
        if uid == "neore_cop":
            assert reg.async_get(entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION
            continue
        state = hass.states.get(entity_id)
        assert state.attributes["friendly_name"] == name
        assert state.attributes.get("unit_of_measurement") == unit


async def test_values_and_energy_classes(hass, gateway):
    await setup_entry(hass, make_entry())
    supplied = hass.states.get("sensor.neore_supplied_power")
    assert float(supplied.state) == 51234.0
    assert supplied.attributes["device_class"] == "energy"
    assert supplied.attributes["state_class"] == "total_increasing"
    power = hass.states.get("sensor.neore_actual_power_usage")
    assert float(power.state) == 4.3 and power.attributes["device_class"] == "power"
    assert float(hass.states.get("sensor.neore_temperature_delta").state) == 5.1
    assert "device_class" not in hass.states.get("sensor.neore_water_pressure").attributes


async def test_map_rename_cannot_rename_legacy(hass, gateway):
    """A map that renames a register id or its HA name changes nothing on the legacy entity."""
    for r in gateway.registers["registers"]:
        if r["id"] == "heat_energy":
            r["id"] = "heat_energy_total"
            r["unit"] = "MWh"
    gateway.state["registers"]["heat_energy_total"] = gateway.state["registers"].pop("heat_energy")
    gateway.install()
    await setup_entry(hass, make_entry())
    state = hass.states.get("sensor.neore_supplied_power")
    assert state.attributes["unit_of_measurement"] == "kWh"
    assert state.attributes["friendly_name"] == "Neore Supplied Power"
    assert float(state.state) == 51234.0
    assert hass.states.get("sensor.neore_heat_energy_total") is None  # no duplicate entity


async def test_new_register_becomes_new_entity(hass, gateway):
    gateway.registers["registers"].append({"id": "dhw_temperature", "unit": "°C", "type": "real", "access": "r",
                                           "derived": False, "deprecated": False, "unique_id": None})
    gateway.state["registers"]["dhw_temperature"] = {"value": 47.5, "quality": "good"}
    gateway.install()
    await setup_entry(hass, make_entry())
    reg = er.async_get(hass)
    entity_id = reg.async_get_entity_id("sensor", "neore", "neore_dhw_temperature")
    assert entity_id == "sensor.neore_dhw_temperature"
    assert float(hass.states.get(entity_id).state) == 47.5
