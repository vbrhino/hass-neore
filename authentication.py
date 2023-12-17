import logging
import hashlib
import requests

_LOGGER = logging.getLogger(__name__)

class NeoreSessionManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(NeoreSessionManager, cls).__new__(cls)
            cls._instance.cookie = None
        return cls._instance

    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password

    def left_rotate(self, n, b):
        return ((n << b) | (n >> (32 - b))) & 0xffffffff

    def f(self, s, x, y, z):
        if s == 0:
            return (x & y) ^ (~x & z) & 0xffffffff
        elif s == 1:
            return x ^ y ^ z
        elif s == 2:
            return (x & y) ^ (x & z) ^ (y & z)
        elif s == 3:
            return x ^ y ^ z

    def to_hex_str(self, val):
        return ''.join(f"{(val >> (i * 4)) & 0xf:x}" for i in range(7, -1, -1))

    def sha1_hash(self, input_string):
        K = [0x5a827999, 0x6ed9eba1, 0x8f1bbcdc, 0xca62c1d6]

        # Ensure input_string is a bytearray
        input_string = bytearray(input_string, 'latin1')
        original_byte_len = len(input_string)
        input_string.append(0x80)

        while len(input_string) % 64 != 56:
            input_string.append(0)

        original_bit_len = original_byte_len * 8
        input_string += original_bit_len.to_bytes(8, byteorder='big')

        h0, h1, h2, h3, h4 = 0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476, 0xc3d2e1f0

        for i in range(0, len(input_string), 64):
            w = [int.from_bytes(input_string[i+j:i+j+4], 'big') for j in range(0, 64, 4)]
            for j in range(16, 80):
                w.append(self.left_rotate(w[j-3] ^ w[j-8] ^ w[j-14] ^ w[j-16], 1))

            a, b, c, d, e = h0, h1, h2, h3, h4

            for j in range(80):
                temp = (self.left_rotate(a, 5) + self.f(j // 20, b, c, d) + e + K[j // 20] + w[j]) & 0xffffffff
                e, d, c, b, a = d, c, self.left_rotate(b, 30), a, temp

            h0, h1, h2, h3, h4 = (h0 + a) & 0xffffffff, (h1 + b) & 0xffffffff, (h2 + c) & 0xffffffff, (h3 + d) & 0xffffffff, (h4 + e) & 0xffffffff

        return self.to_hex_str(h0) + self.to_hex_str(h1) + self.to_hex_str(h2) + self.to_hex_str(h3) + self.to_hex_str(h4)

    def login(self):
        if not self.cookie:
            # Step 1: Make a GET request to retrieve the SoftPLC cookie
            try:
                get_response = requests.get(f"{self.url}LOGIN.XML", verify=False)
                softplc_cookie = get_response.cookies['SoftPLC']
            except requests.RequestException as e:
                _LOGGER.error(f"Error during GET request for cookie: {e}")
                return None

            # Step 2: Use the SoftPLC cookie value in the hash
            payload_hash = self.sha1_hash(softplc_cookie + self.password)

            # Step 3: Make the POST request with the updated payload
            payload = {
                'USER': self.username,
                'PASS': payload_hash
            }

            try:
                post_response = requests.post(f"{self.url}LOGIN.XML", data=payload, verify=False, cookies={'SoftPLC': softplc_cookie})
                _LOGGER.warning(f"Login: {post_response.status_code}, Response: {post_response.text}")
                if post_response.status_code == 200 and 'SoftPLC' in post_response.cookies:
                    self.cookie = post_response.cookies['SoftPLC']
                    _LOGGER.debug("Login successful.")
                else:
                    _LOGGER.warning(f"Login failed. Status code: {post_response.status_code}, Response: {post_response.text}")
            except requests.RequestException as e:
                _LOGGER.error(f"Error during POST login: {e}")

        return self.cookie

# Usage example:
# session_manager = NeoreSessionManager("http://192.168.0.152/", "your_username", "your_password")
# cookie = session_manager.login()
