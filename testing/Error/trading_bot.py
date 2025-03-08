import time
import logging
from gateio_api import GateIOAPIClient
from gateio_websocket import GateIOWebSocketClient
from ui_order_placement import UIOrderPlacement

class OrderState:
    def __init__(self):
        self.active = False
        self.order_type = None  # 'buy' or 'sell'
        self.last_price = None
        self.order_id = None

class TradingCore:
    def __init__(self, driver, config):
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
        try:
            ticker = self.api.exchange.fetch_ticker(self.api.symbol)
            return float(ticker['last'])
        except Exception as e:
            self.logger.critical(f"Initial price fetch failed: {str(e)}")
            raise SystemExit(1)

    def update_price(self, price):
        self.current_price = price

    def _calculate_prices(self, last_price, order_type):
        if order_type == 'buy':
            trigger = last_price * (1 + self.config['trading'][order_type]['trigger_price_adjust'] / 100)
            limit = last_price * (1 + self.config['trading'][order_type]['limit_price_adjust'] / 100)
        elif order_type == 'sell':
            trigger = last_price * (1 - self.config['trading'][order_type]['trigger_price_adjust'] / 100)
            limit = last_price * (1 - self.config['trading'][order_type]['limit_price_adjust'] / 100)
        return trigger, limit

    def _place_new_order(self):
        last_price = self._get_market_price()
        order_type = 'buy' if self.state.order_type != 'buy' else 'sell'
        trigger, limit = self._calculate_prices(last_price, order_type)
        
        order = self.api.place_stop_limit_order(order_type, trigger, limit)
        if order:
            self.state.active = True
            self.state.order_type = order_type
            self.state.last_price = last_price
            self.state.order_id = order['id']

    def _monitor_active_order(self, order):
        current_price = self._get_market_price()
        if self.state.order_type == 'buy' and current_price < self.state.last_price:
            self.logger.info("Price dropped below last price, cancelling buy order")
            self._cancel_and_replace(order)
            return
        elif self.state.order_type == 'sell' and current_price > self.state.last_price:
            self.logger.info("Price rose above last price, cancelling sell order")
            self._cancel_and_replace(order)
            return

    def _cancel_and_replace(self, order):
        try:
            if self.api.cancel_order(order['id']):
                self.state.active = False
                new_price = self._get_market_price()
                trigger, limit = self._calculate_prices(new_price, self.state.order_type)
                
                new_order = self.api.place_stop_limit_order(
                    self.state.order_type, trigger, limit
                )
                if new_order:
                    self.state.last_price = new_price
                    self.state.active = True
                    self.state.order_id = new_order['id']
        except Exception as e:
            self.logger.error(f"Replace failed: {str(e)}")
            self._recover_state()

    def _handle_order_execution(self):
        self.logger.info("Order executed successfully")
        self.state.active = False
        self.state.order_type = 'sell' if self.state.order_type == 'buy' else 'buy'

    def _get_market_price(self):
        start_time = time.time()
        while self.current_price is None:
            if time.time() - start_time > 5:
                self.logger.error("No price update received from websocket within 5 seconds.")
                break
            time.sleep(0.01)
        return self.current_price

    def _recover_state(self):
        self.logger.info("Attempting state recovery...")
        self.api.cancel_all_orders(self.config['trading']['currency_pair'])
        self.state = OrderState()
        self.driver.refresh()
        from selenium.webdriver.support.ui import WebDriverWait  # local import to avoid circular dependency issues
        WebDriverWait(self.driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

    def manage_orders(self):
        trade_count = 0
        max_trades = self.config['trading'].get('trade_limit', None)
        while True:
            if max_trades is not None and trade_count >= max_trades:
                self.logger.info("Trade limit reached. Exiting trading loop.")
                break
            try:
                open_orders = self.api.get_open_orders()
                if not open_orders:
                    if not self.state.active:
                        self._place_new_order()
                    else:
                        self._handle_order_execution()
                else:
                    self._monitor_active_order(open_orders[0])
                trade_count += 1
                time.sleep(0.1)
            except KeyboardInterrupt:
                self.logger.info("Stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error: {str(e)}")
                self._recover_state() 
