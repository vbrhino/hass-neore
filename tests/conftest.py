"""Test setup. The integration lives in custom_components/neore; its parent goes on the
`custom_components` package path, which the harness may already have claimed for its testing_config."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import custom_components  # noqa: E402  # may resolve to the harness's testing_config package

if str(REPO / "custom_components") not in list(custom_components.__path__):
    custom_components.__path__.append(str(REPO / "custom_components"))

from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

URL = "http://gateway.test:8470"
TOKEN = "s3cret-token"
FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


HEALTH = {"status": "ok", "version": "0.1.0", "map_version": 1, "plc": "online"}

# rw registers for the write paths; the default map has none yet.
RW_REGISTERS = [
    {"id": "dhw_setpoint", "unit": "°C", "type": "real", "access": "rw", "derived": False, "min": 40.0,
     "max": 55.0, "max_step": 2.0, "approved": False, "deprecated": False, "write_mode": "shadow",
     "unique_id": None, "meaning": "DHW setpoint"},
    {"id": "backup_heater_enable", "unit": None, "type": "bool", "access": "rw", "derived": False, "min": None,
     "max": None, "max_step": None, "approved": False, "deprecated": False, "write_mode": "live",
     "unique_id": None, "meaning": "Backup heater allowed"},
    {"id": "operating_mode", "unit": None, "type": "enum", "access": "rw", "derived": False, "min": None,
     "max": None, "max_step": None, "approved": False, "deprecated": False, "write_mode": "shadow",
     "unique_id": None, "meaning": "Mode", "options": {"0": "off", "1": "heating", "2": "auto"}},
]
RW_STATE = {
    "dhw_setpoint": {"value": 48.0, "unit": "°C", "ts": 1792500000.0, "quality": "good", "access": "rw"},
    "backup_heater_enable": {"value": False, "unit": None, "ts": 1792500000.0, "quality": "good", "access": "rw"},
    "operating_mode": {"value": "heating", "unit": None, "ts": 1792500000.0, "quality": "good", "access": "rw"},
}

DERIVED = {
    "ts": 1792500000.0, "mode": "heating",
    "electric_kw": {"value": 1.4, "low": 1.1, "high": 1.8, "label": "afgeleid", "basis": "P1 steps vs R7070, n=42"},
    "cop": {"value": None, "low": None, "high": None, "label": "onbekend", "basis": "too few samples"},
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


class FakeGateway:
    """Programs aioclient_mock as a neore-gateway; nothing leaves the process."""

    def __init__(self, mock):
        self.mock = mock
        self.registers = load("registers.json")
        self.state = load("state.json")
        self.derived: dict | None = None

    def with_rw(self) -> FakeGateway:
        self.registers["registers"] += copy.deepcopy(RW_REGISTERS)
        self.state["registers"].update(copy.deepcopy(RW_STATE))
        self.state["modes"] = {"dhw_setpoint": "shadow", "backup_heater_enable": "live", "operating_mode": "shadow"}
        return self

    def install(self, *, down: bool = False, write: tuple[int, dict] | None = None,
                write_exc: Exception | None = None) -> None:
        import aiohttp

        self.mock.clear_requests()
        if down:
            for path in ("health", "state", "registers", "derived"):
                self.mock.get(f"{URL}/api/{path}", exc=aiohttp.ClientConnectionError())
            return
        self.mock.get(f"{URL}/api/health", json=HEALTH)
        self.mock.get(f"{URL}/api/registers", json=self.registers)
        self.mock.get(f"{URL}/api/state", json=self.state)
        if self.derived is None:
            self.mock.get(f"{URL}/api/derived", status=404, json={"error": "not_found"})
        else:
            self.mock.get(f"{URL}/api/derived", json=self.derived)
        if write_exc is not None:
            self.mock.post(f"{URL}/api/write", exc=write_exc)
            return
        status, body = write or (200, {"result": "applied", "register": "x", "mode": "live", "applied": True})
        self.mock.post(f"{URL}/api/write", status=status, json=body)

    def posts(self) -> list:
        return [c for c in self.mock.mock_calls if c[0] == "POST"]


@pytest.fixture
def gateway(aioclient_mock) -> FakeGateway:
    gw = FakeGateway(aioclient_mock)
    gw.install()
    return gw


def make_entry(token: str | None = None) -> MockConfigEntry:
    data = {"url": URL}
    if token:
        data["token"] = token
    return MockConfigEntry(domain="neore", unique_id="neore", title="Neore", data=data)


async def setup_entry(hass, entry: MockConfigEntry) -> MockConfigEntry:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
