"""Short outages keep the last values; more than 3 failed polls -> unavailable + repair issue.
A reading that is not `good`, or a PLC the gateway reports offline, is unavailable at once."""
import pytest

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers import entity_registry as er, issue_registry as ir

from conftest import TOKEN, make_entry, setup_entry

ENTITY = "sensor.neore_supplied_power"


async def _poll(hass, entry):
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()


async def test_unavailable_after_three_failed_polls(hass, gateway):
    entry = await setup_entry(hass, make_entry())
    issues = ir.async_get(hass)
    gateway.install(down=True)
    for _ in range(3):
        await _poll(hass, entry)
        assert hass.states.get(ENTITY).state == "51234.0"
        assert issues.async_get_issue("neore", "gateway_unreachable") is None

    await _poll(hass, entry)
    assert hass.states.get(ENTITY).state == STATE_UNAVAILABLE
    assert issues.async_get_issue("neore", "gateway_unreachable") is not None

    gateway.install()
    await _poll(hass, entry)
    assert hass.states.get(ENTITY).state == "51234.0"
    assert issues.async_get_issue("neore", "gateway_unreachable") is None


async def test_gateway_down_at_startup_retries(hass, gateway):
    from homeassistant.config_entries import ConfigEntryState

    gateway.install(down=True)
    entry = make_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.parametrize("quality", ["bad", "stale", "missing"])
async def test_reading_not_good_is_unavailable(hass, gateway, quality):
    gateway.state["registers"]["heat_energy"] = {"value": 51234.0, "quality": quality}
    gateway.install()
    await setup_entry(hass, make_entry())
    assert hass.states.get(ENTITY).state == STATE_UNAVAILABLE
    assert float(hass.states.get("sensor.neore_water_flow").state) == 1.25


async def test_register_absent_from_state_is_unavailable(hass, gateway):
    del gateway.state["registers"]["heat_energy"]
    gateway.install()
    await setup_entry(hass, make_entry())
    assert hass.states.get(ENTITY).state == STATE_UNAVAILABLE


async def test_writable_with_stale_reading_is_unavailable(hass, gateway):
    gateway.with_rw()
    gateway.state["registers"]["dhw_setpoint"]["quality"] = "stale"
    gateway.install()
    await setup_entry(hass, make_entry(TOKEN))
    eid = er.async_get(hass).async_get_entity_id("number", "neore", "neore_dhw_setpoint")
    assert hass.states.get(eid).state == STATE_UNAVAILABLE


async def test_plc_offline_unavailable_and_repair_after_three_polls(hass, gateway):
    entry = await setup_entry(hass, make_entry())
    issues = ir.async_get(hass)
    gateway.state["plc"] = "offline"
    gateway.install()
    for _ in range(3):
        await _poll(hass, entry)
        assert hass.states.get(ENTITY).state == STATE_UNAVAILABLE
        assert issues.async_get_issue("neore", "plc_offline") is None

    await _poll(hass, entry)
    assert issues.async_get_issue("neore", "plc_offline") is not None
    assert issues.async_get_issue("neore", "gateway_unreachable") is None

    gateway.state["plc"] = "online"
    gateway.install()
    await _poll(hass, entry)
    assert hass.states.get(ENTITY).state == "51234.0"
    assert issues.async_get_issue("neore", "plc_offline") is None


async def test_failing_derived_does_not_fail_polls(hass, gateway):
    from conftest import URL

    entry = await setup_entry(hass, make_entry())
    gateway.mock.clear_requests()
    gateway.mock.get(f"{URL}/api/state", json=gateway.state)
    gateway.mock.get(f"{URL}/api/derived", status=500)
    gateway.mock.get(f"{URL}/api/boost", status=404)
    for _ in range(5):
        await _poll(hass, entry)
    assert hass.states.get(ENTITY).state == "51234.0"
    assert ir.async_get(hass).async_get_issue("neore", "gateway_unreachable") is None
