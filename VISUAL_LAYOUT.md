# Visual Layout of Heat Pump Flow Card

## Card Structure

```
┌─────────────────────────────────────────────────────────┐
│  Neore Warmtepomp Visualisatie                         │  ← Title
├─────────────────────────────────────────────────────────┤
│                                                          │
│    ┌───────┐                                            │
│    │       │    → → → →    ┌─────────┐   → → →         │
│    │ NEORE │  [45.2°C]     │ BUFFER  │                 │
│    │   ⊕   │               │  TANK   │   [HVAC LOAD]   │
│    │       │    ← ← ← ←    │         │   ← ← ←         │
│    └───────┘    [38.5°C]   └─────────┘                 │
│   Heat Pump                                             │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  Metrics Dashboard:                                     │
│  ┌─────────────┬─────────────┬─────────────┐           │
│  │ Power Input │ Thermal Out │    COP      │           │
│  │   3.2 kW    │   12.8 kW   │    4.00     │           │
│  └─────────────┴─────────────┴─────────────┘           │
│  ┌─────────────┬─────────────┬─────────────┐           │
│  │  Flow Rate  │   Energy    │    Cost     │           │
│  │  1.5 m³/h   │  45.2 kWh   │  € 12.34    │           │
│  └─────────────┴─────────────┴─────────────┘           │
└─────────────────────────────────────────────────────────┘
```

## Color Coding

### Heat Pump States
- **Grey** (#95a5a6) - Off/Idle
- **Red** (#e74c3c) - Heating Mode
- **Blue** (#3498db) - Cooling Mode
- **Orange** (#e67e22) - DHW Mode (if configured)
- **Yellow** (#f1c40f) - Defrost Mode (if configured)

### Pipe Colors (Temperature-Based)
- **Red** (#e74c3c) - Hot water (>30°C)
- **Blue** (#3498db) - Cold water (<10°C)
- **Grey** (#95a5a6) - Neutral (10-30°C)

### Animation
```
Flow Direction (when active):
  Heat Pump → Buffer Tank → HVAC Load
       ↓                         ↑
       └─────────────────────────┘
       
  White dots (●) flow along pipes
  Speed proportional to actual flow rate
  Auto-stop when flow < 0.1 m³/h
```

## Interactive Elements

### Temperature Indicators
- Circular badges at key points
- Click to view history graph (future enhancement)
- Updates in real-time

### Metrics Cards
- Color-coded backgrounds
- Large, easy-to-read values
- Auto-updating from sensors

## Responsive Design
- SVG scales to container width
- Maintains aspect ratio
- Works on mobile and desktop
- Minimum recommended width: 400px

## Example Configurations

### Small Dashboard Widget (Compact)
```yaml
type: custom:heat-pump-flow-card
title: Warmtepomp
heat_pump:
  power_entity: sensor.neore_actual_power_usage
  outlet_temp_entity: sensor.neore_output_temperature
  inlet_temp_entity: sensor.neore_input_temperature
  flow_rate_entity: sensor.neore_water_flow
  display_name: "Neore"
heat_pump_visual:
  show_metrics: false  # Hide metrics for compact view
```

### Full Dashboard (Detailed)
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
  show_metrics: true
  animate_fan: true
buffer_tank:
  supply_temp_entity: sensor.buffer_supply_temp
  return_temp_entity: sensor.buffer_return_temp
  name: "BUFFERVAT"
animation:
  enabled: true
```

## Real-World Example (Belgian Setup)

For a typical Belgian home with:
- Floor heating system
- Buffer tank
- Supply temperature: 40-45°C
- Return temperature: 35-38°C
- Flow rate: 1.2 m³/h
- COP: 4.5

The card would show:
```
┌────────────────────────────────────┐
│  Warmtepomp Vloerverwarming        │
├────────────────────────────────────┤
│  [Heat Pump] → 42.5°C → [Buffer]  │
│              ← 37.2°C ←             │
│                                     │
│  Power: 2.8 kW  |  COP: 4.50       │
│  Flow: 1.2 m³/h |  Δ T: 5.3°C      │
└────────────────────────────────────┘
```

## Technical Notes

- SVG viewBox: `0 0 600 400` (aspect ratio 3:2)
- Font: Courier New (monospace for numbers)
- Animation: 60 FPS via requestAnimationFrame
- Updates: Every 30 seconds (sensor polling interval)
- Size: ~18 KB JavaScript (uncompressed)
