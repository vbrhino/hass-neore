"""Neore heat pump via neore-gateway. The gateway owns the PLC session; this integration only reads its REST API."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .const import CONF_TOKEN, CONF_URL, DOMAIN, ISSUE_UNREACHABLE, ISSUE_YAML
from .coordinator import NeoreConfigEntry, NeoreCoordinator, NeoreRuntime
from .gateway import GatewayClient, GatewayError

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.NUMBER, Platform.SELECT, Platform.SWITCH]

# The legacy `neore:` block (host/plc_url, username, password) is accepted only to migrate it.
CONFIG_SCHEMA = vol.Schema({vol.Optional(DOMAIN): vol.Any(dict, None)}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    if DOMAIN not in config:
        return True
    ir.async_create_issue(
        hass, DOMAIN, ISSUE_YAML,
        is_fixable=False, severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_YAML,
        learn_more_url="https://github.com/vbrhino/hass-neore#migrating-from-yaml",
    )
    # Only a marker: PLC host and credentials are never copied into the config entry.
    hass.async_create_task(
        hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_IMPORT}, data={})
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: NeoreConfigEntry) -> bool:
    client = GatewayClient(async_get_clientsession(hass), entry.data[CONF_URL], entry.data.get(CONF_TOKEN))
    try:
        reg = await client.registers()
    except GatewayError as err:
        raise ConfigEntryNotReady(f"neore-gateway unreachable at {client.url}: {err}") from err
    coordinator = NeoreCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = NeoreRuntime(
        client=client,
        coordinator=coordinator,
        registers=[r for r in (reg or {}).get("registers", []) if isinstance(r, dict) and r.get("id")],
        map_version=(reg or {}).get("map_version"),
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NeoreConfigEntry) -> bool:
    ir.async_delete_issue(hass, DOMAIN, ISSUE_UNREACHABLE)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
