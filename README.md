# Neore Heatpump for Home Assistant

Home Assistant integration for a NeoRé heat pump (Tecomat Foxtrot PLC), as a thin client of
[neore-gateway](https://github.com/vbrhino/neore-gateway).

**The gateway is required.** The PLC allows one session per user; the gateway holds it, within a load
budget, and this integration only reads the gateway's REST API. The integration never logs in to the PLC.

## Install

- HACS: add this repository as a custom repository (category *Integration*), install, restart.
- Manual: copy `custom_components/neore/` to `<config>/custom_components/neore/`, restart.

Then *Settings > Devices & services > Add integration > Neore Heatpump*:

| Field | |
|---|---|
| Gateway URL | e.g. `http://192.168.1.10:8470`; validated via `GET /api/health` |
| API token | optional; the gateway's bearer token. Without it, writable registers are not exposed. Checked with a dry-run `POST /api/write?dry_run=1` on a register that does not exist (nothing is written) |

Change either later via *Neore > Reconfigure*. When the gateway answers a write with 401, Home Assistant asks for the new
token (re-authentication).

## Migrating from YAML

The `neore:` block (`host`, `username`, `password`) is no longer used.

1. Run neore-gateway with the PLC credentials (see its README). Stop any other PLC client first.
2. Update this integration and restart. The YAML block is imported once into a config entry at
   `http://127.0.0.1:8470`; the PLC host and credentials are **not** copied. A repair issue says so.
3. If the gateway runs elsewhere: *Neore > Reconfigure*, set the URL.
4. Remove the `neore:` block from `configuration.yaml` and restart; the repair issue disappears.

Existing entities keep their `unique_id`, `entity_id`, name and unit, so history, long-term statistics and
the Energy dashboard continue.

## Entities

| Entity | Unit | Note |
|---|---|---|
| `sensor.neore_object_temperature` | °C | |
| `sensor.neore_outdoor_temperature` | °C | |
| `sensor.neore_circulation_percent` | % | |
| `sensor.neore_outdoor_unit_circulation_percent` | % | |
| `sensor.neore_output_temperature` | °C | supply |
| `sensor.neore_input_temperature` | °C | return |
| `sensor.neore_required_temperature` | °C | |
| `sensor.neore_water_flow` | m³/h | |
| `sensor.neore_actual_power_usage` | kW | **heat** output, not electricity |
| `sensor.neore_supplied_power` | kWh | cumulative **heat**, not electricity |
| `sensor.neore_water_pressure` | Bar | |
| `sensor.neore_temperature_delta` | °C | supply − return, computed by the gateway |
| `sensor.neore_cop` | | deprecated (heat/heat); disabled on new installs |

These 13 are pinned in `custom_components/neore/const.py` (`LEGACY`); a register map change cannot rename them.

- Other registers in the gateway map become sensors (`neore_<register id>`).
- With `/api/derived` on the gateway: `Neore Electric Power Estimate` (kW) and `Neore COP Estimate`, with
  attributes `low`, `high`, `label`, `basis`. Label `onbekend` → state unknown.
- `access: rw` registers (API token required) become `number` (real/int) or `switch` (bool); enum
  registers get no entity yet.
  - On/off and mode registers (type `bool`, or an id containing `mode`, `on_off`, `power`, `enable`) start
    **disabled**; enable them deliberately.
  - A numeric register without both `min` and `max` in the map gets no entity (warning in the log). Attributes show `write_mode` (shadow/live), `min`, `max`, `max_step`.

## Writes

- Every write is `POST /api/write` with the bearer token; the gateway's WriteGuard decides.
- Nothing is written at startup or on restore.
- Each write is sent once, never retried.
- A WriteGuard refusal (HTTP 409) raises an error with the gateway's `result` (`interlock`, `step_too_large`,
  `killswitch`, …); nothing reached the PLC.
- `mismatch`/`error` (HTTP 502): the value was sent but the readback failed or differed. A timeout or dropped
  connection: unknown whether the write was applied. In both cases check the sensor and the gateway audit
  log before trying again.
- In `shadow` mode a write is audited as `would_write` and not sent; the service call says so.

## Unreachable gateway or PLC

Values stay for 3 failed polls (30 s each). From the 4th, entities are unavailable and a repair issue opens;
the first good poll closes it.

A register whose `quality` in `/api/state` is not `good` (`stale`, `bad`, `missing`) is unavailable, so an
old value never looks current. When the gateway reports `plc: offline`, all entities are unavailable at
once; after 3 such polls a *Neore PLC offline* repair issue opens.

Diagnostics (token redacted): *Neore > ⋮ > Download diagnostics*.

## Tests

```
python3.13 -m venv .venv && .venv/bin/pip install pytest-homeassistant-custom-component
.venv/bin/pytest tests
```

Fake gateway only (`aioclient_mock`); no network.
