DOMAIN = 'neore'

from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_HOST
from homeassistant.helpers.discovery import load_platform
from .plc_data_manager import NeoreDataManager

# Default values
DEFAULT_URL = "http://192.168.0.152/"

def setup(hass, config):
    """Set up the Neore component."""
    data_manager = NeoreDataManager(
        config[DOMAIN].get(CONF_HOST, DEFAULT_URL),
        config[DOMAIN][CONF_USERNAME],
        config[DOMAIN][CONF_PASSWORD]
    )

    # Store configuration in hass.data for use in platform setup
    hass.data[DOMAIN] = {
        'data_manager': data_manager
    }

    # Setup the sensor platform
    load_platform(hass, 'sensor', DOMAIN, {}, config)

    return True
