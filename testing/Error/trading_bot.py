import time
import json
import threading
import logging
import websocket
import requests
import hashlib
import hmac
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlencode
from gateio_api import GateIOAPIClient

############################################
# WebSocket Client for Real-Time Price Feed
############################################

class GateIOWebSocketClient:
    def __init__(self, currency_pair, on_price_callback, api_key, api_secret):
        """
        Initializes the authenticated WebSocket client.
        :param currency_pair: e.g. "BTC_USDT" (will be converted to BTCUSDT)
        :param on_price_callback: Function to handle price updates
        :param api_key: Gate.io API key (32 characters)
        :param api_secret: Gate.io API secret (40 characters)
        """
        if len(api_key) != 32 or len(api_secret) != 40:
            raise ValueError("Invalid API credentials format")

        self.api_key = api_key
        self.api_secret = api_secret
        self.currency_pair = currency_pair.replace('_', '')  # Convert to BTCUSDT format
        self.on_price_callback = on_price_callback
        self.ws_url = "wss://ws.gate.io/v4"
        self.ws = None
        self.thread = None
        self.price_lock = threading.Lock()
        self.current_price = None
        self.logger = logging.getLogger("GateIOWebSocketClient")

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            if data.get('channel') != 'spot.tickers' or data.get('event') != 'update':
                return
            
            result = data.get('result', {})
            last_price = result.get('last')
            if not last_price:
                return
            
            try:
                price = float(last_price)
                with self.price_lock:
                    self.current_price = price
                    self.on_price_callback(price)
            except (ValueError, TypeError) as e:
                self.logger.error(f"Price parse error: {e}")
            
        except Exception as e:
            self.logger.error(f"Message processing failed: {e}")

    def on_error(self, ws, error):
        self.logger.error(f"WebSocket Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        self.logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")

    def on_open(self, ws):
        """Send authenticated subscription message"""
        try:
            timestamp = int(time.time())
            signature_payload = f"channel=spot.tickers&event=subscribe&time={timestamp}"
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                signature_payload.encode('utf-8'),
                hashlib.sha512
            ).hexdigest()

            sub_msg = {
                "time": timestamp,
                "channel": "spot.tickers",
                "event": "subscribe",
                "payload": [self.currency_pair],
                "auth": {
                    "method": "api_key",
                    "KEY": self.api_key,
                    "SIGN": signature
                }
            }
            ws.send(json.dumps(sub_msg))
        except Exception as e:
            self.logger.error(f"Subscription failed: {str(e)}")

    def run(self):
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.run_forever(
            ping_interval=30,
            ping_timeout=10,
            ping_payload="keepalive"
        )

    def update_price(self, price):
        with self.price_lock:
            self.current_price = price
        
    def start(self):
        def run_forever():
            retry_count = 0
            while True:
                try:
                    self.run()
                    retry_count = 0  # Reset on successful connection
                except Exception as e:
                    retry_count += 1
                    timeout = min(2 ** retry_count, 30)  # Exponential backoff
                    self.logger.error(f"Reconnecting in {timeout}s: {e}")
                    time.sleep(timeout)
    
        self.thread = threading.Thread(target=run_forever, daemon=True)
        self.thread.start()

############################################
# Trading Bot with WebSocket Price Updates
############################################

class OrderState:
    def __init__(self):
        self.active = False
        self.order_type = None  # 'buy' or 'sell'
        self.last_price = None
        self.order_id = None

class TradingCore:
    def __init__(self, driver, config):
        self.driver = driver
        self.config = config
        self.api = GateIOAPIClient(config)
        self.state = OrderState()
        self.logger = logging.getLogger("TradingCore")
        self.current_price = None

        # Initialize WebSocket client with credentials
        self.ws_client = GateIOWebSocketClient(
            currency_pair=self.config['trading']['currency_pair'],
            on_price_callback=self.update_price,
            api_key=self.config['api']['key'],
            api_secret=self.config['api']['secret']
        )
        self.ws_client.start()
        self.current_price = self._fetch_initial_price()
        
    def _fetch_initial_price(self):
        """Get initial price via REST API"""
        try:
            endpoint = "/spot/tickers"
            query = urlencode({'currency_pair': self.config['trading']['currency_pair']})
            url = f"{self.api.base_url}{endpoint}?{query}"
            headers = self.api._generate_signature('GET', endpoint, query)
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return float(response.json()[0]['last'])
        except Exception as e:
            self.logger.critical(f"Initial price fetch failed: {str(e)}")
            raise SystemExit(1)

    def update_price(self, price):
        self.current_price = price

    # Rest of the TradingCore class remains the same as provided
    # [Keep all existing methods unchanged from _calculate_prices to manage_orders]

    # ... (All other methods remain identical to your original code) import time
import json
import threading
import logging
import websocket
import requests
import hashlib
import hmac
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlencode
from gateio_api import GateIOAPIClient

############################################
# WebSocket Client for Real-Time Price Feed
############################################

class GateIOWebSocketClient:
    def __init__(self, currency_pair, on_price_callback, api_key, api_secret):
        """
        Initializes the authenticated WebSocket client.
        :param currency_pair: e.g. "BTC_USDT" (will be converted to BTCUSDT)
        :param on_price_callback: Function to handle price updates
        :param api_key: Gate.io API key (32 characters)
        :param api_secret: Gate.io API secret (40 characters)
        """
        if len(api_key) != 32 or len(api_secret) != 40:
            raise ValueError("Invalid API credentials format")

        self.api_key = api_key
        self.api_secret = api_secret
        self.currency_pair = currency_pair.replace('_', '')  # Convert to BTCUSDT format
        self.on_price_callback = on_price_callback
        self.ws_url = "wss://ws.gate.io/v4"
        self.ws = None
        self.thread = None
        self.price_lock = threading.Lock()
        self.current_price = None
        self.logger = logging.getLogger("GateIOWebSocketClient")

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            if data.get('channel') != 'spot.tickers' or data.get('event') != 'update':
                return
            
            result = data.get('result', {})
            last_price = result.get('last')
            if not last_price:
                return
            
            try:
                price = float(last_price)
                with self.price_lock:
                    self.current_price = price
                    self.on_price_callback(price)
            except (ValueError, TypeError) as e:
                self.logger.error(f"Price parse error: {e}")
            
        except Exception as e:
            self.logger.error(f"Message processing failed: {e}")

    def on_error(self, ws, error):
        self.logger.error(f"WebSocket Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        self.logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")

    def on_open(self, ws):
        """Send authenticated subscription message"""
        try:
            timestamp = int(time.time())
            signature_payload = f"channel=spot.tickers&event=subscribe&time={timestamp}"
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                signature_payload.encode('utf-8'),
                hashlib.sha512
            ).hexdigest()

            sub_msg = {
                "time": timestamp,
                "channel": "spot.tickers",
                "event": "subscribe",
                "payload": [self.currency_pair],
                "auth": {
                    "method": "api_key",
                    "KEY": self.api_key,
                    "SIGN": signature
                }
            }
            ws.send(json.dumps(sub_msg))
        except Exception as e:
            self.logger.error(f"Subscription failed: {str(e)}")

    def run(self):
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.run_forever(
            ping_interval=30,
            ping_timeout=10,
            ping_payload="keepalive"
        )

    def update_price(self, price):
        with self.price_lock:
            self.current_price = price
        
    def start(self):
        def run_forever():
            retry_count = 0
            while True:
                try:
                    self.run()
                    retry_count = 0  # Reset on successful connection
                except Exception as e:
                    retry_count += 1
                    timeout = min(2 ** retry_count, 30)  # Exponential backoff
                    self.logger.error(f"Reconnecting in {timeout}s: {e}")
                    time.sleep(timeout)
    
        self.thread = threading.Thread(target=run_forever, daemon=True)
        self.thread.start()

############################################
# Trading Bot with WebSocket Price Updates
############################################

class OrderState:
    def __init__(self):
        self.active = False
        self.order_type = None  # 'buy' or 'sell'
        self.last_price = None
        self.order_id = None

class TradingCore:
    def __init__(self, driver, config):
        self.driver = driver
        self.config = config
        self.api = GateIOAPIClient(config)
        self.state = OrderState()
        self.logger = logging.getLogger("TradingCore")
        self.current_price = None

        # Initialize WebSocket client with credentials
        self.ws_client = GateIOWebSocketClient(
            currency_pair=self.config['trading']['currency_pair'],
            on_price_callback=self.update_price,
            api_key=self.config['api']['key'],
            api_secret=self.config['api']['secret']
        )
        self.ws_client.start()
        self.current_price = self._fetch_initial_price()
        
    def _fetch_initial_price(self):
        """Get initial price via REST API"""
        try:
            endpoint = "/spot/tickers"
            query = urlencode({'currency_pair': self.config['trading']['currency_pair']})
            url = f"{self.api.base_url}{endpoint}?{query}"
            headers = self.api._generate_signature('GET', endpoint, query)
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return float(response.json()[0]['last'])
        except Exception as e:
            self.logger.critical(f"Initial price fetch failed: {str(e)}")
            raise SystemExit(1)

    def update_price(self, price):
        self.current_price = price

    # Rest of the TradingCore class remains the same as provided
    # [Keep all existing methods unchanged from _calculate_prices to manage_orders]

    # ... (All other methods remain identical to your original code) 
