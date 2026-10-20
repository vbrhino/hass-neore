"""Base for rw registers (number/switch). Every write is a POST /api/write through the gateway's
WriteGuard; nothing here writes on its own (no restore, no startup write)."""
from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .coordinator import NeoreConfigEntry, NeoreCoordinator
from .entity import NeoreRegisterEntity, display_name
from .gateway import GatewayAuthError, GatewayClient, GatewayError, GatewayWriteRefused

_LOGGER = logging.getLogger(__name__)


def writable_registers(entry: NeoreConfigEntry, match: Callable[[dict[str, Any]], bool]) -> list[dict[str, Any]]:
    """rw registers of one kind; none without an API token (the gateway would refuse every write)."""
    runtime = entry.runtime_data
    regs = [r for r in runtime.registers if r.get("access") == "rw" and not r.get("derived") and match(r)]
    if regs and not runtime.client.has_token:
        _LOGGER.info("No API token configured: %d writable register(s) not exposed", len(regs))
        return []
    return regs


class NeoreWritable(NeoreRegisterEntity):
    def __init__(self, coordinator: NeoreCoordinator, client: GatewayClient, register: dict[str, Any]) -> None:
        super().__init__(coordinator, register.get("unique_id") or f"neore_{register['id']}", display_name(register))
        self._client = client
        self._register = register
        self._register_id: str = register["id"]
        self._attr_entity_registry_enabled_default = not register.get("deprecated")

    @property
    def current(self) -> Any:
        return self._reading().get("value")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        reg = self._register
        return {
            "write_mode": self.coordinator.data.mode(self._register_id) or reg.get("write_mode"),
            "quality": self._reading().get("quality"),
            "min": reg.get("min"),
            "max": reg.get("max"),
            "max_step": reg.get("max_step"),
            "approved": reg.get("approved"),
            "killswitch": self.coordinator.data.state.get("killswitch"),
        }

    async def _async_write(self, value: Any) -> None:
        """POST /api/write; a refusal surfaces the gateway's `result` code as a service error."""
        try:
            res = await self._client.write(self._register_id, value, f"Home Assistant: {self.entity_id}")
        except GatewayWriteRefused as err:
            raise HomeAssistantError(
                f"neore-gateway refused write to {self._register_id}: {err.result}"
                + (f" ({err.detail})" if err.detail else "")
            ) from err
        except GatewayAuthError as err:
            raise HomeAssistantError(f"neore-gateway rejected the API token: {err}") from err
        except GatewayError as err:
            raise HomeAssistantError(f"neore-gateway unreachable: {err}") from err
        await self.coordinator.async_request_refresh()
        if not res.get("applied"):
            # shadow mode: validated and audited as would_write, never sent to the PLC
            raise HomeAssistantError(
                f"{self._register_id} is in {res.get('mode') or 'shadow'} mode: write audited as "
                f"{res.get('result')}, not sent to the heat pump"
            )


def check_step(register: dict[str, Any], current: Any, value: float) -> None:
    """Pre-check of the gateway's max_step guard, so the UI fails fast; the gateway still decides."""
    step = register.get("max_step")
    if step is None or not isinstance(current, (int, float)) or isinstance(current, bool):
        return
    if abs(float(value) - float(current)) > float(step) + 1e-9:
        raise ServiceValidationError(
            f"{register['id']}: change {value - current:+g} exceeds max_step {step:g} (current {current:g})"
        )
