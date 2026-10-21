"""Config flow, reconfigure and the YAML import."""
import pytest

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
    (call,) = gateway.posts()  # token checked with a dry run on a register that does not exist
    assert call[1].query["dry_run"] == "1"
    assert call[2]["register"] == "__neore_token_check__"
    assert call[3]["Authorization"] == f"Bearer {TOKEN}"
    await hass.async_block_till_done()


async def test_user_step_without_token_skips_check(hass, gateway):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"url": URL})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert gateway.posts() == []
    await hass.async_block_till_done()


@pytest.mark.parametrize(("status", "body"), [
    (200, {"result": "not_allowed", "register": "__neore_token_check__", "applied": False}),  # dry run
    (404, {"error": "unknown_register"}),
    (409, {"result": "not_allowed", "register": "__neore_token_check__", "applied": False}),
])
async def test_token_accepted_unless_401(hass, gateway, status, body):
    gateway.install(write=(status, body))
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"url": URL, "token": TOKEN})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()


async def test_user_step_invalid_token(hass, gateway):
    gateway.install(write=(401, {"error": "unauthorized", "detail": None}))
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"url": URL, "token": "wrong"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_sets_new_token(hass, gateway):
    entry = make_entry("old")
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "reauth_confirm"
    gateway.install(write=(401, {"error": "unauthorized", "detail": None}))
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"token": "still-wrong"})
    assert result["errors"] == {"base": "invalid_auth"}
    gateway.install()
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"token": TOKEN})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "reauth_successful"
    assert entry.data == {"url": URL, "token": TOKEN}
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
