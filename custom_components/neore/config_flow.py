"""Config flow: the URL of a neore-gateway, plus an optional API token for writes."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from collections.abc import Mapping

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .const import CONF_TOKEN, CONF_URL, DEFAULT_URL, DEVICE_NAME, DOMAIN
from .gateway import GatewayAuthError, GatewayClient, GatewayError, normalize_url


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
        client = GatewayClient(async_get_clientsession(self.hass), data[CONF_URL], data.get(CONF_TOKEN))
        try:
            health = await client.health()
        except GatewayError:
            return data, {"base": "cannot_connect"}
        if not isinstance(health, dict) or "status" not in health:
            return data, {"base": "not_a_gateway"}
        return data, await self._check_token(client)

    @staticmethod
    async def _check_token(client: GatewayClient) -> dict[str, str]:
        if not client.has_token:
            return {}
        try:
            await client.check_token()
        except GatewayAuthError:
            return {"base": "invalid_auth"}
        except GatewayError:
            return {"base": "cannot_connect"}
        return {}

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

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Started when the gateway answers a write with 401."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            token = (user_input.get(CONF_TOKEN) or "").strip()
            client = GatewayClient(async_get_clientsession(self.hass), entry.data[CONF_URL], token)
            errors = await self._check_token(client) if token else {"base": "invalid_auth"}
            if not errors:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_TOKEN: token})
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({
                vol.Required(CONF_TOKEN): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            }),
            description_placeholders={"url": entry.data[CONF_URL]},
            errors=errors,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Legacy `neore:` YAML block. Creates an entry at the default gateway URL, reachable or not.

        The PLC host and credentials are deliberately dropped; fix the URL via Reconfigure.
        """
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=DEVICE_NAME, data={CONF_URL: DEFAULT_URL})
