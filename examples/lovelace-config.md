# Example Lovelace Card Configuration for Neore Heat Pump

## Basic Configuration (Minimal)
```yaml
type: custom:heat-pump-flow-card
title: Neore Warmtepomp

heat_pump:
  power_entity: sensor.neore_actual_power_usage
  cop_entity: sensor.neore_cop
  outlet_temp_entity: sensor.neore_output_temperature
  inlet_temp_entity: sensor.neore_input_temperature
  flow_rate_entity: sensor.neore_water_flow
  display_name: "Neore"
  # Optional: thermal_entity for thermal output display
  # thermal_entity: sensor.neore_supplied_power
```

## Recommended Configuration (Belgian Setup)
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
  show_metrics: true
  animate_fan: true

animation:
  enabled: true
  max_flow_rate_value: 3.0    # Adjust based on your system (m³/h)
  idle_threshold: 0.1

temperature:
  unit: "C"
  delta_threshold: 10
```

## With Buffer Tank
```yaml
type: custom:heat-pump-flow-card
title: Neore Warmtepomp met Buffervat

heat_pump:
  power_entity: sensor.neore_actual_power_usage
  thermal_entity: sensor.neore_supplied_power
  cop_entity: sensor.neore_cop
  outlet_temp_entity: sensor.neore_output_temperature
  inlet_temp_entity: sensor.neore_input_temperature
  flow_rate_entity: sensor.neore_water_flow
  display_name: "Neore"

heat_pump_visual:
  show_metrics: true
  heating_color: "#e74c3c"

buffer_tank:
  supply_temp_entity: sensor.buffer_tank_supply_temperature
  return_temp_entity: sensor.buffer_tank_return_temperature
  name: "BUFFERVAT"
  gradient:
    enabled: true
    min_temp: 15
    max_temp: 55
    bottom_color: "#95a5a6"
    heating_top_color: "#e74c3c"

animation:
  enabled: true
  max_flow_rate_value: 2.5

temperature:
  unit: "C"
```

## Notes for Belgian Users

### Typical Flow Rates
- **Floor Heating**: 0.5 - 1.5 m³/h
- **Radiator System**: 1.0 - 2.5 m³/h
- **Mixed Systems**: 1.5 - 3.0 m³/h

Set `max_flow_rate_value` in the animation section to match your system's maximum flow rate for optimal animation speed.

### Temperature Settings
- **Floor Heating**: Supply temp 35-45°C
- **Radiators**: Supply temp 45-55°C
- **Buffer Tank Range**: Typically 15-55°C

### Sensor Naming
If you've renamed your sensors, update the entity IDs accordingly:
- `sensor.neore_*` is the default naming pattern
- Check your sensor names in **Developer Tools** → **States**

### Language
The card supports custom labels. You can translate any text by using the appropriate configuration options (see full README for details).
