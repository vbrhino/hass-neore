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

    # Store data manager in hass.data for use in platform setup
    hass.data[DOMAIN] = data_manager
    
    _LOGGER.info("Neore data manager stored, loading sensor platform")

    # Load sensor platform
    # Import here to avoid circular imports
    from homeassistant.helpers import discovery
    
    # Load the platform - await it to ensure proper error handling
    try:
        await discovery.async_load_platform(hass, 'sensor', DOMAIN, None, config)
        _LOGGER.info("Neore sensor platform loaded successfully")
    except Exception as e:
        _LOGGER.error(
            "Failed to load Neore sensor platform: %s. "
            "Check your configuration and restart Home Assistant. "
            "If the issue persists, check that the sensor component is properly loaded.",
            e, 
            exc_info=True
        )
        # Don't fail setup if sensor platform fails
    
    return True
