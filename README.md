# Neore Heat Pump Integration with Flow Visualization Card

Home Assistant custom integration for Neore heat pumps with an animated flow visualization card.

## Features

### Integration Features
- 🌡️ **Temperature Monitoring** - Input, output, outdoor, and object temperatures
- 💧 **Water Flow Monitoring** - Real-time flow rate tracking
- ⚡ **Power Monitoring** - Actual power usage and supplied power (energy)
- 📊 **Calculated Metrics** - COP (Coefficient of Performance) and temperature delta
- 🔄 **Circulation Monitoring** - Indoor and outdoor unit circulation percentages
- 💨 **Pressure Monitoring** - Water pressure tracking

### Flow Card Features
- 🎨 **Animated Water Flow** - Visual dots moving along pipes at speeds proportional to flow rates
- 🌡️ **Temperature-Based Colors** - Pipes change color based on water temperature
- 📍 **Temperature Indicators** - Real-time temperatures at critical points
- 🔥 **State-Based Coloring** - Heat pump changes color based on operating mode
- 🏠 **Complete Circuit Visualization** - Shows heat pump → heating load → return (with or without buffer tank)
- 🛢️ **Buffer Tank Support** - Optional buffer tank visualization with temperature gradients
- 📊 **Real-Time Metrics** - Power, thermal output, COP, and flow rate display
- ⚙️ **Highly Configurable** - Customize colors, animation speeds, and display options
- 📐 **Two Layout Modes** - Simple direct circuit or advanced with buffer tank

## Installation

### Method 1: HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots menu (⋮) in the top right
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/vbrhino/hass-neore`
6. Category: "Integration"
7. Click "Add"
8. Search for "Neore Heatpump"
9. Click "Download"
10. Restart Home Assistant

### Method 2: Manual Installation

1. Copy the entire `hass-neore` folder to your `config/custom_components/` directory
2. Ensure the structure is: `config/custom_components/neore/`
3. Copy `www/heat-pump-flow-card.js` to your `config/www/` directory
4. Restart Home Assistant

## Integration Configuration

Add to your `configuration.yaml`:

```yaml
neore:
  host: "http://192.168.0.152"  # Your Neore heat pump IP address
  username: !secret neore_username
  password: !secret neore_password
```

Add credentials to your `secrets.yaml`:

```yaml
neore_username: your_username
neore_password: your_password
```

Restart Home Assistant after configuration.

## Available Sensors

After setup, the following sensors will be available:

| Sensor | Entity ID | Unit | Description |
|--------|-----------|------|-------------|
| Object Temperature | `sensor.neore_object_temperature` | °C | Room/object temperature |
| Outdoor Temperature | `sensor.neore_outdoor_temperature` | °C | Outside temperature |
| Output Temperature | `sensor.neore_output_temperature` | °C | Heat pump outlet temperature |
| Input Temperature | `sensor.neore_input_temperature` | °C | Heat pump inlet temperature |
| Required Temperature | `sensor.neore_required_temperature` | °C | Target temperature setpoint |
| Water Flow | `sensor.neore_water_flow` | m³/h | Water flow rate |
| Actual Power Usage | `sensor.neore_actual_power_usage` | kW | Current electrical power consumption |
| Supplied Power | `sensor.neore_supplied_power` | kWh | Total energy supplied (cumulative) |
| Water Pressure | `sensor.neore_water_pressure` | Bar | System water pressure |
| Circulation Percent | `sensor.neore_circulation_percent` | % | Indoor unit circulation |
| Outdoor Unit Circulation | `sensor.neore_outdoor_unit_circulation_percent` | % | Outdoor unit circulation |
| Temperature Delta | `sensor.neore_temperature_delta` | °C | Temperature difference (output - input) |
| COP | `sensor.neore_cop` | - | Coefficient of Performance |

## Flow Card Installation

### Add Resource to Lovelace

1. Go to **Settings** → **Dashboards** → **Resources** (top right menu)
2. Click **Add Resource**
3. URL: `/local/heat-pump-flow-card.js`
4. Resource type: **JavaScript Module**
5. Click **Create**

Or add manually to your Lovelace configuration:

```yaml
resources:
  - url: /local/heat-pump-flow-card.js
    type: module
```

## Flow Card Configuration

### Understanding the Visualization Modes

The card automatically adapts to show the appropriate layout:

**Simple Mode (No Buffer Tank)**
- Shows: Heat Pump → Heating Load (Radiators/Floor Heating) → Return to Heat Pump
- Perfect for direct heating systems without buffer tank
- Complete circuit visualization with inlet/outlet temperatures
- Animated flow showing water circulation

**Advanced Mode (With Buffer Tank)**
- Shows: Heat Pump → Buffer Tank → Heating Load → Return
- For systems with intermediate buffer storage
- Additional temperature monitoring points
- Requires `buffer_tank` configuration section

### Basic Configuration (Belgian Setup)

Add this card to your Lovelace dashboard:

```yaml
type: custom:heat-pump-flow-card
title: Neore Warmtepomp Visualisatie

heat_pump:
  power_entity: sensor.neore_actual_power_usage
  thermal_entity: sensor.neore_supplied_power
  cop_entity: sensor.neore_cop
  outlet_temp_entity: sensor.neore_output_temperature
  inlet_temp_entity: sensor.neore_input_temperature
  flow_rate_entity: sensor.neore_water_flow
  display_name: "Neore Warmtepomp"

heat_pump_visual:
  off_color: "#95a5a6"
  heating_color: "#e74c3c"
  cooling_color: "#3498db"
  show_metrics: true
  animate_fan: true

animation:
  enabled: true
  min_flow_rate: 5
  max_flow_rate: 1
  max_flow_rate_value: 3.0
  idle_threshold: 0.1
  dot_size: 1.5
  dot_color: "rgba(255, 255, 255, 0.75)"
  dot_opacity: 1.0

temperature:
  delta_threshold: 10
  hot_color: "#e74c3c"
  cold_color: "#3498db"
  neutral_color: "#95a5a6"
  unit: "C"

display:
  show_values: true
  show_labels: true
  decimal_places: 1
```

### With Buffer Tank (Optional)

If you have buffer tank temperature sensors, add this section:

```yaml
buffer_tank:
  supply_temp_entity: sensor.buffer_tank_supply_temperature
  return_temp_entity: sensor.buffer_tank_return_temperature
  name: "BUFFERVAT"
  label_color: "#ffffff"
  label_font_size: 12
  gradient:
    enabled: true
    levels: 10
    min_temp: 10
    max_temp: 60
    bottom_color: "#95a5a6"
    heating_top_color: "#e74c3c"
```

### Full Configuration Example

For advanced users who want all options:

```yaml
type: custom:heat-pump-flow-card
title: Neore Warmtepomp Systeem

heat_pump:
  power_entity: sensor.neore_actual_power_usage
  thermal_entity: sensor.neore_supplied_power
  cop_entity: sensor.neore_cop
  outlet_temp_entity: sensor.neore_output_temperature
  inlet_temp_entity: sensor.neore_input_temperature
  flow_rate_entity: sensor.neore_water_flow
  display_name: "Neore Warmtepomp"

heat_pump_visual:
  off_color: "#95a5a6"          # Grey when off
  heating_color: "#e74c3c"      # Red when heating
  cooling_color: "#3498db"      # Blue when cooling
  dhw_color: "#e67e22"          # Orange for DHW mode
  show_metrics: true
  animate_fan: true

buffer_tank:
  supply_temp_entity: sensor.buffer_supply_temp
  return_temp_entity: sensor.buffer_return_temp
  name: "BUFFERVAT"
  label_color: "#ffffff"
  gradient:
    enabled: true
    levels: 10
    min_temp: 10
    max_temp: 60
    bottom_color: "#95a5a6"
    heating_top_color: "#e74c3c"

hvac:
  thermal_entity: sensor.hvac_thermal_power
  flow_rate_entity: sensor.hvac_flow_rate
  supply_temp_entity: sensor.hvac_supply_temp
  return_temp_entity: sensor.hvac_return_temp

animation:
  enabled: true
  min_flow_rate: 5              # Slower animation
  max_flow_rate: 1              # Faster animation
  max_flow_rate_value: 3.0      # Flow rate for max speed (m³/h)
  idle_threshold: 0.1           # Stop animation below this flow
  dot_size: 1.5
  use_temp_color: false
  dot_color: "rgba(255, 255, 255, 0.75)"
  dot_opacity: 1.0

temperature:
  delta_threshold: 10           # °C difference for hot/cold colors
  hot_color: "#e74c3c"
  cold_color: "#3498db"
  neutral_color: "#95a5a6"
  unit: "C"

temperature_status:
  enabled: true
  circle_radius: 12
  points:
    hp_outlet:
      enabled: true
    hp_inlet:
      enabled: true
    buffer_supply:
      enabled: true
    buffer_return:
      enabled: true

text_style:
  font_family: "Courier New, monospace"
  font_size: 11
  font_weight: "bold"

display:
  show_values: true
  show_labels: true
  show_icons: true
  compact: false
  decimal_places: 1
```

## Configuration Options

### Heat Pump Section (`heat_pump`)

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `power_entity` | string | Yes | Electrical power input sensor |
| `thermal_entity` | string | No | Thermal power output sensor |
| `cop_entity` | string | No | COP sensor |
| `outlet_temp_entity` | string | Yes | Outlet temperature sensor |
| `inlet_temp_entity` | string | Yes | Inlet temperature sensor |
| `flow_rate_entity` | string | Yes | Water flow rate sensor |
| `display_name` | string | No | Display name for heat pump |

### Heat Pump Visual (`heat_pump_visual`)

| Option | Default | Description |
|--------|---------|-------------|
| `off_color` | `#95a5a6` | Color when heat pump is off |
| `heating_color` | `#e74c3c` | Color when heating |
| `cooling_color` | `#3498db` | Color when cooling |
| `show_metrics` | `true` | Show metrics below visualization |
| `animate_fan` | `true` | Animate the fan icon |

### Animation Section (`animation`)

| Option | Default | Description |
|--------|---------|-------------|
| `enabled` | `true` | Enable flow animation |
| `min_flow_rate` | `5` | Animation delay at max flow (slower) |
| `max_flow_rate` | `1` | Animation delay at min flow (faster) |
| `max_flow_rate_value` | `50` | Flow rate value for maximum speed |
| `idle_threshold` | `0` | Stop animation below this flow rate |
| `dot_size` | `1.5` | Size of animated dots |
| `dot_color` | `rgba(255,255,255,0.75)` | Color of animated dots |

### Temperature Section (`temperature`)

| Option | Default | Description |
|--------|---------|-------------|
| `delta_threshold` | `10` | Temperature difference from room temp (20°C) for hot/cold colors (°C) |
| `hot_color` | `#e74c3c` | Color for hot pipes (above room temp + threshold) |
| `cold_color` | `#3498db` | Color for cold pipes (below room temp - threshold) |
| `neutral_color` | `#95a5a6` | Color for neutral temperature (within threshold range) |
| `unit` | `C` | Temperature unit (C or F) |

## Belgian Context

This integration is ideal for Belgian homes with heat pump installations. Typical configurations:

- **Floor Heating Systems** - Monitor low-temperature heating circuits
- **Buffer Tank Integration** - Common in Belgian installations for better efficiency
- **Energy Monitoring** - Track consumption for accurate utility billing
- **Climate Zones** - Optimized for Belgian climate conditions

### Typical Belgian Heat Pump Settings

- **Heating Mode**: Supply temperature 35-45°C (floor heating) or 45-55°C (radiators)
- **Flow Rates**: 0.5-2.0 m³/h for residential systems
- **COP**: Expect 3.0-5.0 depending on outdoor temperature
- **Operating Range**: -10°C to +35°C outdoor temperature

## Troubleshooting

### Integration Issues

**Problem**: Sensors not appearing
- **Solution**: Check that `configuration.yaml` is correct and restart Home Assistant
- Verify the heat pump IP address is accessible from Home Assistant
- Check credentials are correct

**Problem**: Sensors show "Unknown" or "Unavailable"
- **Solution**: Check heat pump network connectivity
- Verify username/password in `secrets.yaml`
- Check Home Assistant logs for authentication errors

### Card Issues

**Problem**: Card not found
- **Solution**: Ensure `heat-pump-flow-card.js` is in `config/www/` directory
- Add the resource in Lovelace resources
- Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)

**Problem**: No data displayed on card
- **Solution**: Verify entity IDs match your sensor names
- Check sensors have valid values in Developer Tools → States
- Ensure sensors are updating (check last_updated timestamp)

**Problem**: Animation not working
- **Solution**: Check flow_rate_entity has valid data
- Verify `animation.enabled` is `true`
- Check flow rate is above `idle_threshold`

## Energy Dashboard Integration

Add your Neore heat pump to the Home Assistant Energy Dashboard:

1. Go to **Settings** → **Dashboards** → **Energy**
2. Click **Add Consumption**
3. Select `sensor.neore_supplied_power`
4. Set device class to "Energy"
5. Click **Save**

This will track your heat pump's energy consumption over time.

## Support

- **Issues**: https://github.com/vbrhino/hass-neore/issues
- **Discussions**: https://github.com/vbrhino/hass-neore/discussions

## License

This project is licensed under the MIT License.

## Credits

- Integration developed for Neore heat pump systems
- Flow card visualization inspired by [jasipsw/heat-pump-flow-card](https://github.com/jasipsw/heat-pump-flow-card)
- Adapted for Belgian home installations

## Changelog

### Version 1.0.0 (2024-01-01)
- Initial release with flow visualization card
- Full Neore heat pump sensor integration
- Belgian-specific configuration examples
- HACS compatibility
- Animated flow visualization
- Temperature-based color coding
- Real-time metrics display
