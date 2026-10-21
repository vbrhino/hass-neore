"""Price-boost status from /api/boost; 404 -> no entity; a failing fetch never fails the poll."""
import copy
from datetime import datetime

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.util import dt as dt_util

from conftest import BOOST, URL, make_entry, setup_entry

ENTITY = "sensor.neore_boost"


async def _poll(hass, entry):
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()


def _local(ts: float) -> str:
    return dt_util.as_local(dt_util.utc_from_timestamp(ts)).isoformat()


async def test_boost_absent_on_older_gateway(hass, gateway):
    await setup_entry(hass, make_entry())
    assert er.async_get(hass).async_get_entity_id("sensor", "neore", "neore_boost") is None
    assert hass.states.get("sensor.neore_supplied_power").state == "51234.0"


async def test_boost_sensor(hass, gateway):
    gateway.boost = copy.deepcopy(BOOST)
    gateway.install()
    await setup_entry(hass, make_entry())
    assert er.async_get(hass).async_get_entity_id("sensor", "neore", "neore_boost") == ENTITY
    st = hass.states.get(ENTITY)
    assert st.state == "planned"
    assert st.attributes["friendly_name"] == "Neore Boost"
    a = st.attributes
    assert (a["enabled"], a["mode"], a["baseline"], a["boost_value"]) == (True, "live", 0.0, 5.0)
    assert a["plan_start"] == _local(1792661400.0)
    assert a["plan_end"] == _local(1792672200.0)
    assert datetime.fromisoformat(a["plan_start"]).utcoffset() is not None
    assert (a["avg_price"], a["ref_avg_price"]) == (0.186, 0.25703)
    assert a["skip_reasons"] == ["one boost per 24 h: last started 20-10 11:30"]
    assert a["last_action_ts"] == _local(1792586000.0)
    assert (a["last_action_result"], a["last_action_value"]) == ("applied", 0.0)


async def test_boost_without_plan_or_action(hass, gateway):
    gateway.boost = BOOST | {"state": "no_prices", "plan": None, "last_action": None,
                             "skip_reasons": ["too few prices for a window"]}
    gateway.install()
    await setup_entry(hass, make_entry())
    a = hass.states.get(ENTITY).attributes
    assert hass.states.get(ENTITY).state == "no_prices"
    assert (a["plan_start"], a["plan_end"], a["avg_price"], a["ref_avg_price"]) == (None, None, None, None)
    assert (a["last_action_ts"], a["last_action_result"], a["last_action_value"]) == (None, None, None)


async def test_boost_follows_polls(hass, gateway):
    gateway.boost = copy.deepcopy(BOOST)
    gateway.install()
    entry = await setup_entry(hass, make_entry())
    gateway.boost = BOOST | {"state": "active", "skip_reasons": []}
    gateway.install()
    await _poll(hass, entry)
    assert hass.states.get(ENTITY).state == "active"


async def test_failing_boost_keeps_last_then_unavailable(hass, gateway):
    gateway.boost = copy.deepcopy(BOOST)
    gateway.install()
    entry = await setup_entry(hass, make_entry())
    gateway.mock.clear_requests()
    gateway.mock.get(f"{URL}/api/state", json=gateway.state)
    gateway.mock.get(f"{URL}/api/derived", status=404)
    gateway.mock.get(f"{URL}/api/boost", status=500)
    for _ in range(3):
        await _poll(hass, entry)
        assert hass.states.get(ENTITY).state == "planned"
    await _poll(hass, entry)
    assert hass.states.get(ENTITY).state == STATE_UNAVAILABLE
    # The rest of the poll is unaffected.
    assert hass.states.get("sensor.neore_supplied_power").state == "51234.0"
    assert ir.async_get(hass).async_get_issue("neore", "gateway_unreachable") is None

    gateway.install()
    await _poll(hass, entry)
    assert hass.states.get(ENTITY).state == "planned"


async def test_boost_ignores_plc_offline(hass, gateway):
    gateway.boost = copy.deepcopy(BOOST)
    gateway.state["plc"] = "offline"
    gateway.install()
    await setup_entry(hass, make_entry())
    assert hass.states.get(ENTITY).state == "planned"
    assert hass.states.get("sensor.neore_supplied_power").state == STATE_UNAVAILABLE


async def test_legacy_unique_ids_untouched(hass, gateway):
    from custom_components.neore.const import LEGACY

    gateway.boost = copy.deepcopy(BOOST)
    gateway.install()
    await setup_entry(hass, make_entry())
    reg = er.async_get(hass)
    assert len(LEGACY) == 13
    for uid in LEGACY:
        assert reg.async_get_entity_id("sensor", "neore", uid) is not None
