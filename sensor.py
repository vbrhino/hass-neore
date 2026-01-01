from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from datetime import timedelta
from . import DOMAIN

SCAN_INTERVAL = timedelta(seconds=30)  # Set the desired update interval (e.g., 30 seconds)

ENERGY_ENDPOINT = "PAGE70.XML"

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup the Neore sensor platform."""
    # Retrieve configuration from hass.data
    data_manager = hass.data[DOMAIN]['data_manager']

    # Create sensor instances
    sensors = [
        NeoreObjectTemperature("Neore Object Temperature", data_manager, ENERGY_ENDPOINT, "__R7195_REAL_.1f"),
        NeoreOutdoorTemperature("Neore Outdoor Temperature", data_manager, ENERGY_ENDPOINT, "__R7079_REAL_.0f"), # 1f is not available in PAGE70.XML
        NeoreCirculationPercent("Neore Circulation Percent", data_manager, ENERGY_ENDPOINT, "__R15173_REAL_.0f"),
        NeoreOutdoorUnitCirculationPercent("Neore Outdoor Unit Circulation Percent", data_manager, ENERGY_ENDPOINT, "__R7070_REAL_.0f"),
        NeoreOutputTemperature("Neore Output Temperature", data_manager, ENERGY_ENDPOINT, "__R15104_REAL_.1f"),
        NeoreInputTemperature("Neore Input Temperature", data_manager, ENERGY_ENDPOINT, "__R7096_REAL_.1f"),
        NeoreRequiredTemperature("Neore Required Temperature", data_manager, ENERGY_ENDPOINT, "__R7312_REAL_.0f"),
        NeoreWaterFlow("Neore Water Flow", data_manager, ENERGY_ENDPOINT, "__R7083_REAL_.1f"),
        NeoreActualPowerUsage("Neore Actual Power Usage", data_manager, ENERGY_ENDPOINT, "__R7087_REAL_.1f"),
        NeoreSuppliedPower("Neore Supplied Power", data_manager, ENERGY_ENDPOINT, "__R7091_REAL_.0f"),
        NeoreWaterPressure("Neore Water Pressure", data_manager, ENERGY_ENDPOINT, "__R7297_REAL_.1f"),
        # Calculated sensors for monitoring efficiency
        NeoreTemperatureDelta("Neore Temperature Delta", data_manager, ENERGY_ENDPOINT, "__R15104_REAL_.1f", "__R7096_REAL_.1f"),
        NeoreCOP("Neore COP", data_manager, ENERGY_ENDPOINT, "__R7083_REAL_.1f", "__R15104_REAL_.1f", "__R7096_REAL_.1f", "__R7087_REAL_.1f"),
    ]

    async_add_entities(sensors)



class NeoreBaseSensor(SensorEntity):
    def __init__(self, name, data_manager, endpoint, field_name):
        self._name = name
        self._state = None
        self._data_manager  = data_manager
        self._endpoint = endpoint
        self._field_name = field_name
        # Generate a unique_id based on the field name
        self._attr_unique_id = f"neore_{field_name}"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state
    
    @property
    def unique_id(self):
        """Return a unique ID for this sensor."""
        return self._attr_unique_id

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return None  # Default to None if not defined in subclass

    def update(self):
        self._state = self._data_manager.get_sensor_data(self._field_name)


### PAGE70.XML

class NeoreObjectTemperature(NeoreBaseSensor): # __R7195_REAL_.1f
    @property
    def unit_of_measurement(self):
        return "°C"
    
    @property
    def suggested_display_precision(self):
        """Return the suggested display precision."""
        return 1

class NeoreOutdoorTemperature(NeoreBaseSensor): # __R7079_REAL_.1f
    @property
    def unit_of_measurement(self):
        return "°C"
    
    @property
    def suggested_display_precision(self):
        """Return the suggested display precision."""
        return 1

class NeoreCirculationPercent(NeoreBaseSensor): # __R15173_REAL_.0f
    @property
    def unit_of_measurement(self):
        return "%"

class NeoreOutdoorUnitCirculationPercent(NeoreBaseSensor): # __R7070_REAL_.0f
    @property
    def unit_of_measurement(self):
        return "%"

class NeoreOutputTemperature(NeoreBaseSensor): # __R15104_REAL_.1f
    @property
    def unit_of_measurement(self):
        return "°C"
    
    @property
    def suggested_display_precision(self):
        """Return the suggested display precision."""
        return 1

class NeoreInputTemperature(NeoreBaseSensor): # __R7096_REAL_.1f
    @property
    def unit_of_measurement(self):
        return "°C"
    
    @property
    def suggested_display_precision(self):
        """Return the suggested display precision."""
        return 1

class NeoreRequiredTemperature(NeoreBaseSensor): # __R7312_REAL_.0f
    @property
    def unit_of_measurement(self):
        return "°C"
    
    @property
    def suggested_display_precision(self):
        """Return the suggested display precision."""
        return 1

class NeoreWaterFlow(NeoreBaseSensor): # __R7083_REAL_.1f
    @property
    def unit_of_measurement(self):
        return "m³/h"
    
    @property
    def suggested_display_precision(self):
        """Return the suggested display precision."""
        return 2

class NeoreActualPowerUsage(NeoreBaseSensor): # __R7087_REAL_.1f
    @property
    def unit_of_measurement(self):
        return "kW"
    
    @property
    def device_class(self):
        """Return the device class."""
        return SensorDeviceClass.POWER
    
    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return SensorStateClass.MEASUREMENT
    
    @property
    def suggested_display_precision(self):
        """Return the suggested display precision."""
        return 2

class NeoreSuppliedPower(NeoreBaseSensor): # __R7091_REAL_.0f
    @property
    def unit_of_measurement(self):
        return "kWh"

    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return SensorStateClass.TOTAL_INCREASING

    @property
    def device_class(self):
        """Return the class of this device."""
        return SensorDeviceClass.ENERGY
    
    @property
    def suggested_display_precision(self):
        """Return the suggested display precision."""
        return 1

class NeoreWaterPressure(NeoreBaseSensor): # __R7297_REAL_.1f
    @property
    def unit_of_measurement(self):
        return "Bar"
    
    @property
    def suggested_display_precision(self):
        """Return the suggested display precision."""
        return 1


### Calculated sensors for monitoring efficiency

class NeoreTemperatureDelta(SensorEntity):
    """Sensor for temperature difference between output and input."""
    
    def __init__(self, name, data_manager, endpoint, output_field, input_field):
        self._name = name
        self._state = None
        self._data_manager = data_manager
        self._endpoint = endpoint
        self._output_field = output_field
        self._input_field = input_field
        self._attr_unique_id = "neore_temperature_delta"
    
    @property
    def name(self):
        return self._name
    
    @property
    def state(self):
        return self._state
    
    @property
    def unique_id(self):
        """Return a unique ID for this sensor."""
        return self._attr_unique_id
    
    @property
    def unit_of_measurement(self):
        return "°C"
    
    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return SensorStateClass.MEASUREMENT
    
    @property
    def suggested_display_precision(self):
        """Return the suggested display precision."""
        return 1
    
    def update(self):
        """Calculate temperature delta."""
        try:
            output_temp = self._data_manager.get_sensor_data(self._output_field)
            input_temp = self._data_manager.get_sensor_data(self._input_field)
            
            if output_temp is not None and input_temp is not None:
                self._state = round(float(output_temp) - float(input_temp), 1)
            else:
                self._state = None
        except (ValueError, TypeError):
            self._state = None


class NeoreCOP(SensorEntity):
    """Sensor for Coefficient of Performance calculation."""
    
    def __init__(self, name, data_manager, endpoint, flow_field, output_field, input_field, power_field):
        self._name = name
        self._state = None
        self._data_manager = data_manager
        self._endpoint = endpoint
        self._flow_field = flow_field
        self._output_field = output_field
        self._input_field = input_field
        self._power_field = power_field
        self._attr_unique_id = "neore_cop"
    
    @property
    def name(self):
        return self._name
    
    @property
    def state(self):
        return self._state
    
    @property
    def unique_id(self):
        """Return a unique ID for this sensor."""
        return self._attr_unique_id
    
    @property
    def unit_of_measurement(self):
        return None
    
    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return SensorStateClass.MEASUREMENT
    
    @property
    def suggested_display_precision(self):
        """Return the suggested display precision."""
        return 2
    
    def update(self):
        """Calculate COP (Coefficient of Performance)."""
        try:
            flow = self._data_manager.get_sensor_data(self._flow_field)
            output_temp = self._data_manager.get_sensor_data(self._output_field)
            input_temp = self._data_manager.get_sensor_data(self._input_field)
            power = self._data_manager.get_sensor_data(self._power_field)
            
            if all(v is not None for v in [flow, output_temp, input_temp, power]):
                flow_val = float(flow)
                temp_diff = float(output_temp) - float(input_temp)
                power_val = float(power)
                
                # Avoid division by zero
                if power_val > 0 and temp_diff > 0:
                    # Thermal power (kW) = flow (m³/h) × temp_diff (°C) × 4.186 (kJ/kg·°C) × density (≈1000 kg/m³) / 3600 (s/h)
                    thermal_power = flow_val * temp_diff * 4.186 * 1000 / 3600
                    cop = thermal_power / power_val
                    self._state = round(cop, 2)
                else:
                    self._state = None
            else:
                self._state = None
        except (ValueError, TypeError, ZeroDivisionError):
            self._state = None


### PAGE69.XML
# class NeoreHoursInUse(NeoreBaseSensor): # __R15676_UDINT_u
#     pass  # No additional implementation needed, uses the base class logic