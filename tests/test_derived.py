"""Estimates from /api/derived; 404 -> no estimate entities."""
from homeassistant.helpers import entity_registry as er

from conftest import DERIVED, make_entry, setup_entry


async def test_derived_absent(hass, gateway):
    await setup_entry(hass, make_entry())
    reg = er.async_get(hass)
    assert reg.async_get_entity_id("sensor", "neore", "neore_derived_electric_kw") is None


async def test_derived_sensors(hass, gateway):
    gateway.derived = DERIVED
    gateway.install()
    await setup_entry(hass, make_entry())
    reg = er.async_get(hass)
    kw = hass.states.get(reg.async_get_entity_id("sensor", "neore", "neore_derived_electric_kw"))
    assert float(kw.state) == 1.4
    assert kw.attributes["unit_of_measurement"] == "kW"
    assert (kw.attributes["low"], kw.attributes["high"], kw.attributes["label"]) == (1.1, 1.8, "afgeleid")
    assert kw.attributes["basis"].startswith("P1")
    cop = hass.states.get(reg.async_get_entity_id("sensor", "neore", "neore_derived_cop"))
    assert cop.state == "unknown"
    assert cop.attributes["label"] == "onbekend"
