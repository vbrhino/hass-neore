DOMAIN = 'neore'

import logging
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from .plc_data_manager import NeoreDataManager

_LOGGER = logging.getLogger(__name__)

# Default values
DEFAULT_URL = "http://192.168.0.152/"

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Neore component."""
    _LOGGER.info("Neore integration setup starting")
    
    if DOMAIN not in config:
        _LOGGER.warning("Neore not configured in configuration.yaml")
        return True
    
    _LOGGER.info("Creating Neore data manager")
    data_manager = NeoreDataManager(
        config[DOMAIN].get(CONF_HOST, DEFAULT_URL),
        config[DOMAIN][CONF_USERNAME],
        config[DOMAIN][CONF_PASSWORD]
    )

    # Store configuration in hass.data for use in platform setup
    hass.data[DOMAIN] = {
        'data_manager': data_manager,
        'config': config[DOMAIN]
    }
    
    _LOGGER.info("Neore data manager stored, setting up sensor entities")

    # Import sensor module and set up sensors directly
    from . import sensor
    
    # Use hass.helpers to set up the platform properly
    # Get the sensor component
    sensor_component = hass.data.get('sensor')
    if sensor_component is None:
        _LOGGER.error("Sensor component not loaded yet")
        return False
    
    # Call the sensor platform setup function directly
    await sensor.async_setup_platform(
        hass, 
        config.get(DOMAIN, {}), 
        sensor_component.async_add_entities,
        None
    )
    
    _LOGGER.info("Neore sensor entities setup complete")

    return True
