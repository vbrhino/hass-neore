# Quick Installation Guide

## Step 1: Install the Integration

### Option A: Via HACS (Recommended)
1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click **⋮** (three dots) → **Custom repositories**
4. Add: `https://github.com/vbrhino/hass-neore`
5. Category: **Integration**
6. Click **Add** → **Download**
7. Restart Home Assistant

### Option B: Manual
1. Copy the `neore` folder to `config/custom_components/`
2. Copy `www/heat-pump-flow-card.js` to `config/www/`
3. Restart Home Assistant

## Step 2: Configure the Integration

Edit `configuration.yaml`:

```yaml
neore:
  host: "http://192.168.0.152"  # Your heat pump IP
  username: !secret neore_username
  password: !secret neore_password
```

Edit `secrets.yaml`:

```yaml
neore_username: your_username
neore_password: your_password
```

Restart Home Assistant.

## Step 3: Add the Card Resource

1. Go to **Settings** → **Dashboards**
2. Click **⋮** (three dots) → **Resources**
3. Click **+ Add Resource**
4. URL: `/local/heat-pump-flow-card.js`
5. Type: **JavaScript Module**
6. Click **Create**

## Step 4: Add the Card to Your Dashboard

1. Edit your dashboard
2. Add a **Manual Card**
3. Paste this configuration:

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

heat_pump_visual:
  heating_color: "#e74c3c"
  show_metrics: true

animation:
  enabled: true
  max_flow_rate_value: 3.0

temperature:
  unit: "C"
```

4. Click **Save**

## Verification

Check that you see:
- ✅ Heat pump visualization with colored pipes
- ✅ Temperature values updating
- ✅ Animated dots flowing when heat pump is running
- ✅ Metrics showing power, COP, and flow rate

## Troubleshooting

**No sensors?**
- Check Home Assistant logs
- Verify heat pump IP address is correct
- Test network connectivity to heat pump

**Card not found?**
- Clear browser cache (Ctrl+Shift+R)
- Verify resource was added correctly
- Check browser console for errors (F12)

**No animation?**
- Verify flow_rate_entity has valid data
- Check that flow rate > 0.1 m³/h
- Ensure animation is enabled in config

## Next Steps

- See `README.md` for full configuration options
- See `examples/lovelace-config.md` for more examples
- Add buffer tank if you have one configured
- Customize colors and animations to your preference

## Support

Issues: https://github.com/vbrhino/hass-neore/issues
