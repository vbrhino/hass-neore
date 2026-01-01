DOMAIN = 'neore'

from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from .plc_data_manager import NeoreDataManager

# Default values
DEFAULT_URL = "http://192.168.0.152/"

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Neore component."""
    if DOMAIN not in config:
        return True
    
    data_manager = NeoreDataManager(
        config[DOMAIN].get(CONF_HOST, DEFAULT_URL),
        config[DOMAIN][CONF_USERNAME],
        config[DOMAIN][CONF_PASSWORD]
    )

    # Store configuration in hass.data for use in platform setup
    hass.data[DOMAIN] = {
        'data_manager': data_manager
    }

    # Setup the sensor platform using async discovery
    await hass.helpers.discovery.async_load_platform('sensor', DOMAIN, {}, config)

    return True
