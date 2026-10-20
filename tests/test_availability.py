"""Short outages keep the last values; more than 3 failed polls -> unavailable + repair issue."""
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers import issue_registry as ir

from conftest import make_entry, setup_entry

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


async def test_missing_value_is_unknown(hass, gateway):
    gateway.state["registers"]["heat_energy"] = {"value": None, "quality": "bad"}
    gateway.install()
    await setup_entry(hass, make_entry())
    assert hass.states.get(ENTITY).state == "unknown"
