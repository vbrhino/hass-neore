"""rw registers: entities only with a token, never a write at startup, writes go to POST /api/write."""
import pytest

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er

from conftest import TOKEN, URL, make_entry, setup_entry


def _eid(hass, domain, uid):
    return er.async_get(hass).async_get_entity_id(domain, "neore", uid)


async def test_no_token_no_writable_entities(hass, gateway):
    gateway.with_rw().install()
    await setup_entry(hass, make_entry())
    assert _eid(hass, "number", "neore_dhw_setpoint") is None
    assert _eid(hass, "switch", "neore_backup_heater_enable") is None
    assert _eid(hass, "sensor", "neore_dhw_setpoint") is None  # rw registers are not mirrored as sensors


async def test_entities_and_no_startup_write(hass, gateway):
    gateway.with_rw().install()
    await setup_entry(hass, make_entry(TOKEN))
    number = hass.states.get(_eid(hass, "number", "neore_dhw_setpoint"))
    assert float(number.state) == 48.0
    assert number.attributes["min"] == 40.0 and number.attributes["max"] == 55.0
    assert number.attributes["max_step"] == 2.0 and number.attributes["write_mode"] == "shadow"
    assert hass.states.get(_eid(hass, "switch", "neore_backup_heater_enable")).state == "off"
    # enum registers get no entity until /api/registers exposes their options
    assert not [e for e in er.async_get(hass).entities.values() if e.unique_id == "neore_operating_mode"]
    assert gateway.posts() == []


async def test_number_write_posts_with_token(hass, gateway):
    gateway.with_rw().install()
    await setup_entry(hass, make_entry(TOKEN))
    await hass.services.async_call("number", "set_value", {
        "entity_id": _eid(hass, "number", "neore_dhw_setpoint"), "value": 49.5}, blocking=True)
    (call,) = gateway.posts()
    assert str(call[1]) == f"{URL}/api/write"
    assert call[2]["register"] == "dhw_setpoint" and call[2]["value"] == 49.5
    assert call[2]["actor"] == "home-assistant"
    assert call[3]["Authorization"] == f"Bearer {TOKEN}"


async def test_switch_write(hass, gateway):
    gateway.with_rw().install()
    await setup_entry(hass, make_entry(TOKEN))
    await hass.services.async_call("switch", "turn_on", {
        "entity_id": _eid(hass, "switch", "neore_backup_heater_enable")}, blocking=True)
    (call,) = gateway.posts()
    assert call[2]["register"] == "backup_heater_enable" and call[2]["value"] is True


async def test_refusal_surfaces_result(hass, gateway):
    gateway.with_rw().install(write=(409, {"result": "interlock", "register": "dhw_setpoint", "applied": False,
                                           "detail": "outdoor_temperature > 0"}))
    await setup_entry(hass, make_entry(TOKEN))
    with pytest.raises(HomeAssistantError, match="interlock"):
        await hass.services.async_call("number", "set_value", {
            "entity_id": _eid(hass, "number", "neore_dhw_setpoint"), "value": 49.0}, blocking=True)


async def test_shadow_write_is_reported(hass, gateway):
    gateway.with_rw().install(write=(200, {"result": "would_write", "register": "dhw_setpoint", "mode": "shadow",
                                           "applied": False}))
    await setup_entry(hass, make_entry(TOKEN))
    with pytest.raises(HomeAssistantError, match="shadow"):
        await hass.services.async_call("number", "set_value", {
            "entity_id": _eid(hass, "number", "neore_dhw_setpoint"), "value": 49.0}, blocking=True)
    assert len(gateway.posts()) == 1


async def test_max_step_and_range_checked_before_post(hass, gateway):
    gateway.with_rw().install()
    await setup_entry(hass, make_entry(TOKEN))
    eid = _eid(hass, "number", "neore_dhw_setpoint")
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call("number", "set_value", {"entity_id": eid, "value": 52.0}, blocking=True)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call("number", "set_value", {"entity_id": eid, "value": 60.0}, blocking=True)
    assert gateway.posts() == []


async def test_bad_token(hass, gateway):
    gateway.with_rw().install(write=(401, {"error": "unauthorized", "detail": None}))
    await setup_entry(hass, make_entry("wrong"))
    with pytest.raises(HomeAssistantError, match="token"):
        await hass.services.async_call("switch", "turn_off", {
            "entity_id": _eid(hass, "switch", "neore_backup_heater_enable")}, blocking=True)
