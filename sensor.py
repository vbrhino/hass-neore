from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
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
    ]

    async_add_entities(sensors)



class NeoreBaseSensor(SensorEntity):
    def __init__(self, name, data_manager, endpoint, field_name):
        self._name = name
        self._state = None
        self._data_manager  = data_manager
        self._endpoint = endpoint
        self._field_name = field_name

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

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

class NeoreOutdoorTemperature(NeoreBaseSensor): # __R7079_REAL_.1f
    @property
    def unit_of_measurement(self):
        return "°C"

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

class NeoreInputTemperature(NeoreBaseSensor): # __R7096_REAL_.1f
    @property
    def unit_of_measurement(self):
        return "°C"

class NeoreRequiredTemperature(NeoreBaseSensor): # __R7312_REAL_.0f
    @property
    def unit_of_measurement(self):
        return "°C"

class NeoreWaterFlow(NeoreBaseSensor): # __R7083_REAL_.1f
    @property
    def unit_of_measurement(self):
        return "m³/h"

class NeoreActualPowerUsage(NeoreBaseSensor): # __R7087_REAL_.1f
    @property
    def unit_of_measurement(self):
        return "kW"

class NeoreSuppliedPower(NeoreBaseSensor): # __R7091_REAL_.0f
    @property
    def unit_of_measurement(self):
        return "kWh"

    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return "total_increasing"

    @property
    def device_class(self):
        """Return the class of this device."""
        return SensorDeviceClass.ENERGY

class NeoreWaterPressure(NeoreBaseSensor): # __R7297_REAL_.1f
    @property
    def unit_of_measurement(self):
        return "Bar"


### PAGE69.XML
# class NeoreHoursInUse(NeoreBaseSensor): # __R15676_UDINT_u
#     pass  # No additional implementation needed, uses the base class logic