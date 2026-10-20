"""Config flow, reconfigure and the YAML import."""
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component

from conftest import TOKEN, URL, make_entry

DOMAIN = "neore"


async def test_user_step_creates_entry(hass, gateway):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"url": URL + "/", "token": TOKEN})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"url": URL, "token": TOKEN}
    await hass.async_block_till_done()


async def test_user_step_cannot_connect(hass, gateway):
    gateway.install(down=True)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"url": URL})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_single_instance(hass, gateway):
    make_entry().add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure_changes_url(hass, gateway):
    entry = make_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"url": URL, "token": TOKEN})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {"url": URL, "token": TOKEN}
    await hass.async_block_till_done()


async def test_yaml_import(hass, aioclient_mock):
    """The owner's block: host/username/password. Entry at the default URL, no PLC credentials kept, repair issue."""
    aioclient_mock.get("http://127.0.0.1:8470/api/registers", status=500)
    config = {DOMAIN: {"host": "http://192.168.0.152/", "username": "admin", "password": "hunter2"}}
    assert await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].data == {"url": "http://127.0.0.1:8470"}
    assert "hunter2" not in str(entries[0].as_dict())
    assert ir.async_get(hass).async_get_issue(DOMAIN, "deprecated_yaml") is not None
    assert not [c for c in aioclient_mock.mock_calls if "192.168.0.152" in str(c[1])]


async def test_yaml_import_once(hass, gateway):
    make_entry().add_to_hass(hass)
    config = {DOMAIN: {"host": "http://192.168.0.152/", "username": "u", "password": "p"}}
    assert await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert ir.async_get(hass).async_get_issue(DOMAIN, "deprecated_yaml") is not None
