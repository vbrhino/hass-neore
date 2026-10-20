"""Config flow: the URL of a neore-gateway, plus an optional API token for writes."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .const import CONF_TOKEN, CONF_URL, DEFAULT_URL, DEVICE_NAME, DOMAIN
from .gateway import GatewayClient, GatewayError, normalize_url


def _schema(url: str, token: str | None) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_URL, default=url): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
        vol.Optional(CONF_TOKEN, description={"suggested_value": token}): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    })


class NeoreConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _validate(self, user_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
        data = {CONF_URL: normalize_url(user_input[CONF_URL])}
        if token := (user_input.get(CONF_TOKEN) or "").strip():
            data[CONF_TOKEN] = token
        try:
            health = await GatewayClient(async_get_clientsession(self.hass), data[CONF_URL]).health()
        except GatewayError:
            return data, {"base": "cannot_connect"}
        if not isinstance(health, dict) or "status" not in health:
            return data, {"base": "not_a_gateway"}
        return data, {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = await self._validate(user_input)
            if not errors:
                return self.async_create_entry(title=DEVICE_NAME, data=data)
        user_input = user_input or {}
        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input.get(CONF_URL, DEFAULT_URL), user_input.get(CONF_TOKEN)),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = await self._validate(user_input)
            if not errors:
                return self.async_update_reload_and_abort(entry, data=data)
        current = user_input or entry.data
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(current.get(CONF_URL, DEFAULT_URL), current.get(CONF_TOKEN)),
            errors=errors,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Legacy `neore:` YAML block. Creates an entry at the default gateway URL, reachable or not.

        The PLC host and credentials are deliberately dropped; fix the URL via Reconfigure.
        """
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=DEVICE_NAME, data={CONF_URL: DEFAULT_URL})
