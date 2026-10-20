"""Base for rw registers (number/switch). Every write is a POST /api/write through the gateway's
WriteGuard; nothing here writes on its own (no restore, no startup write)."""
from __future__ import annotations

from collections.abc import Callable
import logging
import re
from typing import Any

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .coordinator import NeoreConfigEntry, NeoreCoordinator
from .entity import NeoreRegisterEntity, display_name
from .gateway import GatewayAuthError, GatewayClient, GatewayError, GatewayWriteRefused, GatewayWriteUnknown

_LOGGER = logging.getLogger(__name__)

# Registers that switch the heat pump or one of its functions on/off, or change its mode.
_SWITCHING_ROLES = {"mode", "on_off", "power"}
_SWITCHING_ID = re.compile(r"(^|_)(mode|on_off|onoff|power|enable|enabled)(_|$)")


def switches_plant(register: dict[str, Any]) -> bool:
    """On/off or mode registers: their entities start disabled, so enabling one is a deliberate act."""
    return (
        register.get("type") == "bool"
        or register.get("role") in _SWITCHING_ROLES
        or bool(_SWITCHING_ID.search(str(register["id"])))
    )


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
        self._attr_entity_registry_enabled_default = not register.get("deprecated") and not switches_plant(register)

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
        """POST /api/write once (never retried); the error text follows the gateway's `result` code."""
        reg = self._register_id
        try:
            res = await self._client.write(reg, value, f"Home Assistant: {self.entity_id}")
        except GatewayWriteRefused as err:
            raise HomeAssistantError(_refusal_text(reg, err)) from err
        except GatewayAuthError as err:
            raise HomeAssistantError(f"neore-gateway rejected the API token: {err}") from err
        except GatewayWriteUnknown as err:
            await self.coordinator.async_request_refresh()
            raise HomeAssistantError(
                f"No answer from neore-gateway for the write to {reg} ({err}): unknown whether it was applied. "
                "Check the sensor and the gateway audit log before trying again."
            ) from err
        except GatewayError as err:
            raise HomeAssistantError(f"neore-gateway unreachable, write to {reg} not sent: {err}") from err
        await self.coordinator.async_request_refresh()
        if res.get("applied"):
            return
        result = res.get("result")
        if result == "would_write" and res.get("mode") == "shadow":
            raise HomeAssistantError(
                f"{reg} is in shadow mode: write validated and audited as would_write, not sent to the heat pump"
            )
        raise HomeAssistantError(f"Write to {reg} not applied: {result}")


def _refusal_text(register_id: str, err: GatewayWriteRefused) -> str:
    detail = f" ({err.detail})" if err.detail else ""
    if err.status == 409:  # WriteGuard refusal: nothing sent to the PLC
        return f"neore-gateway refused the write to {register_id}: {err.result}{detail}"
    if err.result == "audit_failed":
        return f"Write to {register_id} not sent: the gateway could not record it in its audit log{detail}"
    # 502 mismatch/error: sent to the PLC, readback failed or differed
    return (f"Write to {register_id} failed after it was sent to the PLC: {err.result}{detail}. "
            "Check the sensor and the gateway audit log before trying again.")


def check_step(register: dict[str, Any], current: Any, value: float) -> None:
    """Pre-check of the gateway's max_step guard, so the UI fails fast; the gateway still decides."""
    step = register.get("max_step")
    if step is None or not isinstance(current, (int, float)) or isinstance(current, bool):
        return
    if abs(float(value) - float(current)) > float(step) + 1e-9:
        raise ServiceValidationError(
            f"{register['id']}: change {value - current:+g} exceeds max_step {step:g} (current {current:g})"
        )
