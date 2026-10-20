# Neore Heatpump for Home Assistant

Home Assistant integration for a NeoRé heat pump with a Tecomat Foxtrot PLC, as a thin client of
[neore-gateway](https://github.com/vbrhino/neore-gateway).

Unofficial: not made or supported by NeoRé or Teco. Writes to the heat pump are at your own risk.

**The gateway is required.** The PLC allows one session per user; the gateway holds it, within a load
budget, and this integration only reads the gateway's REST API. The integration never logs in to the PLC.
The gateway must be the **only** PLC client: stop the old YAML integration and any other tool polling the
PLC web server, or they take each other's session.

Tested hardware: NeoRé heat pump with Tecomat Foxtrot PLC, TECO Web Server v11.0. One installation; other
models or firmware may expose different pages and registers (steps 2-3 below find them).

## Getting started

Details for steps 1-4 are in the [neore-gateway README](https://github.com/vbrhino/neore-gateway#readme).

1. **Install the gateway** on an always-on Linux host with Docker on the same LAN as the PLC: clone
   neore-gateway, `python3.13 -m venv .venv && .venv/bin/pip install -e .` for the CLI.
2. **Probe and discover the PLC** (credentials file `USER=`/`PASS=`, mode 600):
   `neore-gateway-cli probe --url http://<plc-ip>/` (one login), then
   `neore-gateway-cli discover --url http://<plc-ip>/` (capped crawl into `./cache/plc`).
3. **Map**: `neore-gateway-cli candidates --yaml` drafts registers from the cache (always `access: r`).
   Copy the bundled `neore-default.yaml`, add/verify registers, point `NEORE_MAP` at it. The default map
   carries the 13 sensors below.
4. **Run the gateway**: in `deploy/`, `.env` with `NEORE_PLC_URL`, secrets `neore_credentials` and
   `api_token`, `APP_UID=$(id -u) docker compose up -d --build`. Check
   `curl http://<gateway-host>:8470/api/health` → `"status": "ok"`, `"plc": "online"`. Every register starts
   in `shadow` mode: writes are validated and audited, never sent.
5. **Remove the old YAML** `neore:` block (if any) and restart Home Assistant; see
   [Migrating from YAML](#migrating-from-yaml) to keep history.
6. **Install this integration**: HACS > custom repository (category *Integration*) > install > restart.
   Manual: copy `custom_components/neore/` to `<config>/custom_components/neore/`.
7. **Add it**: *Settings > Devices & services > Add integration > Neore Heatpump*.

| Field | |
|---|---|
| Gateway URL | see below; validated via `GET /api/health` |
| API token | optional; the content of the gateway's `api_token` secret. Without it, writable registers are not exposed. Checked with a dry-run `POST /api/write?dry_run=1` on a register that does not exist (nothing is written) |

Gateway URL:

| Home Assistant runs | Gateway runs | URL |
|---|---|---|
| HAOS, or any install | on another host | `http://<gateway-host-ip>:8470` |
| Docker, host network | same machine | `http://127.0.0.1:8470` (the default) |

With `NEORE_HTTP_HOST=127.0.0.1` the gateway only answers on its own host: HAOS on another host cannot reach it.

Change either field later via *Neore > Reconfigure*. When the gateway answers a write with 401, Home Assistant
asks for the new token (re-authentication).

## Security

LAN only. The gateway speaks plain `http`; the token travels as a bearer header in clear text. Its GET routes
(values, map, health) have no authentication and bind `0.0.0.0` by default. Run it on a trusted LAN or
loopback, never expose port 8470 to the internet, and rotate the token if it may have leaked.

## Migrating from YAML

The `neore:` block (`host`, `username`, `password`) is no longer used.

1. Run neore-gateway with the PLC credentials (see its README). Stop any other PLC client first.
2. Update this integration and restart. The YAML block is imported once into a config entry at
   `http://127.0.0.1:8470`; the PLC host and credentials are **not** copied. A repair issue says so.
3. If the gateway runs elsewhere: *Neore > Reconfigure*, set the URL.
4. Remove the `neore:` block from `configuration.yaml` and restart; the repair issue disappears.

Existing entities keep their `unique_id`, `entity_id`, name and unit, so history, long-term statistics and
the Energy dashboard continue.

Names stay full ("Neore Water Flow") with `has_entity_name` off: with it on, Home Assistant would prefix the
device name ("Neore Neore Water Flow") and create new entity ids.

Added metadata: the YAML integration set no device or state class on most sensors. This one adds
`device_class` `temperature` (6 temperature sensors) and `volume_flow_rate` (water flow), and
`state_class: measurement` on those 7 plus both percentages and water pressure. Home Assistant starts
long-term statistics for them from the update; existing history is untouched. Actual power usage, supplied
power, temperature delta and COP keep the classes they had.

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
- Shadow or live per register: the `write_mode` attribute of its entity. Switching to `live` is done on the
  gateway only (map approval + `POST /api/mode` with a confirmation), never from Home Assistant.

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
