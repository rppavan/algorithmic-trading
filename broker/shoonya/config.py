from NorenRestApiPy.NorenApi import *
import logging
import pyotp
import os
from dotenv import load_dotenv

load_dotenv()

class ShoonyaApiPy(NorenApi):
    def __init__(self):
        NorenApi.__init__(self, host='https://api.shoonya.com/NorenWClientTP/', websocket='wss://api.shoonya.com/NorenWSTP/')
        global api
        api = self

    # Expose the WebSocket instance
    @property
    def ws(self):
        return self.websocket

logging.basicConfig(level=logging.INFO)  # Enable debug to see request and responses

api = ShoonyaApiPy()  # Start of our program

def login():
    # Generation of TOTP and Initializing it to "otp"
    token = os.getenv('SHOONYA_TOTP_TOKEN')  # Token to generate totp
    otp = pyotp.TOTP(token).now()  # TOTP is generated & loaded into otp variable

    # Login credentials from environment variables
    user = os.getenv('SHOONYA_USER')
    pwd = os.getenv('SHOONYA_PWD')
    vc = os.getenv('SHOONYA_VC')
    app_key = os.getenv('SHOONYA_APP_KEY')
    imei = os.getenv('SHOONYA_IMEI')

    # print(user, pwd, otp, vc, app_key, imei)

    # Calling Login Method on api Instance (created at the start of the program)
    ret = api.login(userid=user, password=pwd, twoFA=otp, vendor_code=vc, api_secret=app_key, imei=imei)
    if ret and ret.get('stat') == 'Ok':
        logging.info("Login successful")
        return ret
    else:
        logging.error(f"Login failed: {ret}")
        return None
    return ret

def logout():
    api.logout()

val = login()
print(val)

def start_websocket(order_update_callback, subscribe_callback, socket_open_callback):
    api.start_websocket(order_update_callback=order_update_callback,
                        subscribe_callback=subscribe_callback,
                        socket_open_callback=socket_open_callback)

def subscribe_instruments(instruments):
    """Subscribe to a list of instruments."""
    if isinstance(instruments, list):
        api.subscribe(instruments)
    else:
        api.subscribe([instruments])  # Wrap single instrument in a list

# Event handlers
def event_handler_feed_update(tick_data):
    print(f"Feed update: {tick_data}")

def event_handler_order_update(tick_data):
    print(f"Order update: {tick_data}")

feed_opened = False

def open_callback():
    global feed_opened
    feed_opened = True