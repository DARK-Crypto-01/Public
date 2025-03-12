import time
import logging
from gateio_api import GateIOAPIClient
from gateio_websocket import GateIOWebSocketClient

class OrderState:
def init(self):
self.active = False
self.order_type = None  # 'buy' or 'sell'
self.last_price = None
self.order_id = None

class TradingCore:
def init(self, config):
self.config = config
self.api = GateIOAPIClient(config)
self.state = OrderState()
self.logger = logging.getLogger("TradingCore")
self.current_price = None
self.logger.info("Initializing TradingCore...")

Initialize WebSocket client with credentials

self.ws_client = GateIOWebSocketClient(
currency_pair=self.config['trading']['currency_pair'],
on_price_callback=self.update_price,
api_key=self.config['api']['key'],
api_secret=self.config['api']['secret']
)
self.ws_client.start()
self.logger.info("WebSocket client started. Fetching initial market price...")
self.current_price = self._fetch_initial_price()
self.logger.info(f"Initial market price: {self.current_price}")

def _fetch_initial_price(self):
try:
ticker = self.api.exchange.fetch_ticker(self.api.symbol)
price = float(ticker['last'])
self.logger.debug(f"Fetched initial ticker: {ticker}")
return price
except Exception as e:
self.logger.critical(f"Initial price fetch failed: {str(e)}")
raise SystemExit(1)

def update_price(self, price):
self.current_price = price
self.logger.debug(f"Price updated via callback: {price}")

def _calculate_prices(self, last_price, order_type):
self.logger.debug(f"Calculating prices for {order_type} order with last price: {last_price}")
if order_type == 'buy':
trigger = last_price * (1 + self.config['trading'][order_type]['trigger_price_adjust'] / 100)
limit = last_price * (1 + self.config['trading'][order_type]['limit_price_adjust'] / 100)
elif order_type == 'sell':
trigger = last_price * (1 - self.config['trading'][order_type]['trigger_price_adjust'] / 100)
limit = last_price * (1 - self.config['trading'][order_type]['limit_price_adjust'] / 100)
self.logger.debug(f"Calculated trigger: {trigger}, limit: {limit}")
return trigger, limit

def _place_new_order(self):
last_price = self._get_market_price()
order_type = self.state.order_type or 'buy'
self.logger.info(f"Placing new {order_type} order based on last price: {last_price}")
trigger, limit = self._calculate_prices(last_price, order_type)

order = self.api.place_stop_limit_order(order_type, trigger, limit)
if order:
self.logger.info(f"New order placed: {order}")
self.state.active = True
self.state.order_type = order_type
self.state.last_price = last_price
self.state.order_id = order['id']
else:
self.logger.error("Failed to place new order.")

def _monitor_active_order(self, order):
current_price = self._get_market_price()
self.logger.debug(f"Monitoring active order. Current price: {current_price}, Order last price: {self.state.last_price}")
if self.state.order_type == 'buy' and current_price < self.state.last_price:
self.logger.info("Price dropped below last price; cancelling buy order.")
self._cancel_and_replace(order)
return
elif self.state.order_type == 'sell' and current_price > self.state.last_price:
self.logger.info("Price rose above last price; cancelling sell order.")
self._cancel_and_replace(order)
return
else:
self.logger.debug("No conditions met for cancellation.")

def _cancel_and_replace(self, order):
self.logger.info(f"Cancelling order: {order['id']} and replacing it.")
try:
if self.api.cancel_order(order['id']):
self.state.active = False
new_price = self._get_market_price()
trigger, limit = self._calculate_prices(new_price, self.state.order_type)
new_order = self.api.place_stop_limit_order(self.state.order_type, trigger, limit)
if new_order:
self.logger.info(f"Replaced order successfully with new order: {new_order}")
self.state.last_price = new_price
self.state.active = True
self.state.order_id = new_order['id']
else:
self.logger.error("Failed to place replacement order.")
else:
self.logger.error("Cancellation of order failed.")
except Exception as e:
self.logger.error(f"Replace failed: {str(e)}")
self._recover_state()

def _handle_order_execution(self):
self.logger.info("Order executed successfully.")
self.state.active = False

Flip order type for next trade

self.state.order_type = 'sell' if self.state.order_type == 'buy' else 'buy'
self.logger.info(f"Next order type set to: {self.state.order_type}")

def _get_market_price(self):
self.logger.debug("Fetching current market price...")
start_time = time.time()
while self.current_price is None:
if time.time() - start_time > 5:
self.logger.error("No price update received from websocket within 5 seconds.")
break
time.sleep(0.01)
self.logger.debug(f"Current market price is: {self.current_price}")
return self.current_price

def _recover_state(self):
self.logger.info("Initiating state recovery...")
max_retries = 3
recovered = False
preserved_order_type = self.state.order_type  # Capture current order type

for attempt in range(max_retries):
try:

1. Cancel all existing orders

canceled = self.api.cancel_all_orders(self.config['trading']['currency_pair'])
open_orders = self.api.get_open_orders()

if open_orders:
self.logger.error(f"Failed to cancel orders: {open_orders}")
raise Exception("Order cancellation failed")

# 2. Reset state while preserving order type        
self.state = OrderState()        
self.state.order_type = preserved_order_type  # Restore order type        
    
# 3. Add fallback to initial state        
if self.state.order_type is None:        
    self.state.order_type = 'buy'  # Default initial state        
        
recovered = True        
break

except Exception as e:
self.logger.error(f"Recovery attempt {attempt+1} failed: {str(e)}")
time.sleep(2 ** attempt)

if not recovered:
self.logger.critical("State recovery failed after multiple attempts!")

Add emergency shutdown logic here

self.logger.info(f"State recovery completed. Resuming with order type: {self.state.order_type}")

def manage_orders(self):
trade_count = 0
max_trades = self.config['trading'].get('trade_limit')

self.logger.info("Starting order management loop.")
while True:
if max_trades is not None and trade_count >= max_trades:
self.logger.info("Trade limit reached. Exiting trading loop.")
break

try:
open_orders = self.api.get_open_orders()
self.logger.debug(f"Open orders: {open_orders}")

if not open_orders:        
    if not self.state.active:        
        self.logger.info("No active orders - placing initial order")        
        self._place_new_order()        
    else:        
        self.logger.info("Order executed successfully")        
        self._handle_order_execution()        
        trade_count += 1  # Only increment when orders complete        
else:        
    self.logger.debug("Monitoring existing orders")        
    self._monitor_active_order(open_orders[0])        

# Use websocket-driven price updates instead of sleep        
time.sleep(self.config['trading']['price_poll_interval'])

except KeyboardInterrupt:
self.logger.info("Stopped by user")
break
except Exception as e:
self.logger.error(f"Error in manage_orders loop: {str(e)}")
self._recover_state()
time.sleep(1)  # Prevent tight error loops
