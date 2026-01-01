import logging
import time
import requests
import xml.etree.ElementTree as ET
from threading import Thread
from .authentication import NeoreSessionManager

_LOGGER = logging.getLogger(__name__)
ENDPOINTS = ['PAGE70.XML']
COOLDOWN_TIME = 30

class NeoreDataManager:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(NeoreDataManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, plc_url, username, password):
        # Only initialize once
        if self._initialized:
            return
            
        self._plc_url = plc_url
        self._username = username
        self._password = password
        self._data_map = {}  # Map to store data
        self._current_endpoint_idx = 0
        self._update_thread = Thread(target=self._update_data)
        self._update_thread.daemon = True
        self._update_thread.start()
        self._initialized = True
        _LOGGER.info("NeoreDataManager initialized and update thread started")

    def _update_data(self):
        _LOGGER.info("NeoreDataManager update thread started")
        while True:
            endpoint = ENDPOINTS[self._current_endpoint_idx]
            cookie = self._login()

            if cookie is not None:
                base_url = self._plc_url if self._plc_url.endswith('/') else self._plc_url + '/'
                response = requests.get(f"{base_url}{endpoint}", cookies={'SoftPLC': cookie})

                if response.status_code == 200:
                    self._process_response(response)
                    _LOGGER.debug("Successfully fetched and processed data from %s", endpoint)
                else:
                    _LOGGER.error("Failed to fetch data from endpoint %s. Status code: %s \n %s", endpoint, response.status_code, response.text)
                self._current_endpoint_idx = (self._current_endpoint_idx + 1) % len(ENDPOINTS)
            else:
                _LOGGER.warning("Login failed, will retry in %d seconds", COOLDOWN_TIME)
            time.sleep(COOLDOWN_TIME)

    def _login(self):
        session_manager = NeoreSessionManager(self._plc_url, self._username, self._password)
        cookie = session_manager.login()
        return cookie

    def _process_response(self, response):
        root = ET.fromstring(response.content)
        count = 0
        for input_element in root.findall('.//INPUT'):
            input_name = input_element.get('NAME')
            input_value = input_element.get('VALUE')
            self._data_map[input_name] = input_value
            count += 1
        _LOGGER.debug("Processed %d input elements from response", count)

    def get_sensor_data(self, input_name):
        return self._data_map.get(input_name)

# Example usage:
# manager = NeoreDataManager('http://192.168.0.152', 'your_username', 'your_password')

# To get data for a specific input_name:
# data = manager.get_sensor_data('__R7195_REAL_.1f')
