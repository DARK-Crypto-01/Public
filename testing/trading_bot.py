import time
import json
import threading
import logging
import websocket
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from gateio_api import GateIOAPIClient

############################################
# WebSocket Client for Real-Time Price Feed
############################################

class GateIOWebSocketClient:
    def __init__(self, currency_pair, on_price_callback):
        """
        Initializes the WebSocket client.
        :param currency_pair: e.g. "BTC_USDT" (must match the subscription format)
        :param on_price_callback: Function to be called with the updated price.
        """
        self.currency_pair = currency_pair
        self.on_price_callback = on_price_callback
        self.ws_url = "wss://api.gateio.ws/ws/v4"
        self.ws = None
        self.thread = None
        # Add thread lock
        self.price_lock = threading.Lock()
        self.logger = logging.getLogger("GateIOWebSocketClient")

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            if data.get('channel') != 'ticker' or data.get('event') != 'update':
                return
            
            result = data.get('result', {})
            if not result.get('last'):
                return
            
            try:
                last_price = float(result['last'])
                with self.price_lock:
                    self.current_price = last_price
                    self.on_price_callback(last_price)
            except (ValueError, KeyError) as e:
                self.logger.error(f"Price parse error: {e}")
            
        except Exception as e:
            self.logger.error(f"Message processing failed: {e}")

    def on_error(self, ws, error):
        print("WebSocket Error:", error)

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket closed:", close_status_code, close_msg)

    def on_open(self, ws):
        # Construct and send a subscription message.
        sub_msg = {
            "time": int(time.time()),
            "channel": "ticker",
            "event": "subscribe",
            "payload": [self.currency_pair]
        }
        ws.send(json.dumps(sub_msg))

    def run(self):
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.run_forever(
            ping_interval=30,  # Send ping every 30 seconds
            ping_timeout=10,    # Wait 10 seconds for pong response
            ping_payload="keepalive"
        )

    def update_price(self, price):
        # Add thread locking for price updates
        with self.price_lock:
            self.current_price = price
        
    def start(self):
        def run_forever():
            while True:  # Proper reconnection loop
                try:
                    self.run()
                except Exception as e:
                    print(f"Reconnecting: {e}")
                    time.sleep(1)
    
        self.thread = threading.Thread(target=run_forever)
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
        self.current_price = None  # Updated via WebSocket

        # Start the WebSocket client to receive live price updates.
        self.ws_client = GateIOWebSocketClient(
            self.config['trading']['currency_pair'], 
            self.update_price
        )
        self.ws_client.start()
        self.current_price = self._fetch_initial_price()
        
    def _fetch_initial_price(self):
        """Get initial price via REST API before WS connects"""
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
        """
        Callback function invoked by the WebSocket client.
        Updates the current market price.
        """
        self.current_price = price

    def _calculate_prices(self, last_price, order_type):
        """
        Calculates trigger and limit prices based on order type.
        For buys, adds the percentages; for sells, subtracts them.
        """
        if order_type == 'buy':
            trigger = last_price * (1 + self.config['trading'][order_type]['trigger_price_adjust'] / 100)
            limit = last_price * (1 + self.config['trading'][order_type]['limit_price_adjust'] / 100)
        elif order_type == 'sell':
            trigger = last_price * (1 - self.config['trading'][order_type]['trigger_price_adjust'] / 100)
            limit = last_price * (1 - self.config['trading'][order_type]['limit_price_adjust'] / 100)
        return trigger, limit

    def _select_conditional_tab(self, order_type):
        conditional_tab_selector = self.config['trading'][order_type]['selectors']['conditional_tab']
        self._click_element(conditional_tab_selector)

    def _select_dropdown_option(self, order_type):
        dropdown_selector = self.config['trading'][order_type]['selectors']['condition_dropdown']
        self._click_element(dropdown_selector)
        if order_type == 'buy':
            option_selector = self.config['trading'][order_type]['selectors']['greater_equal_option']
        else:
            option_selector = self.config['trading'][order_type]['selectors']['less_equal_option']
        self._click_element(option_selector)

    def _adjust_slider_to_full(self, order_type):
        slider_selector = self.config['trading'][order_type]['selectors']['amount_slider']
        slider = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, slider_selector))
        )
        # Get the slider percentage from the config file
        slider_percentage = self.config["trading"]["slider_percentage"]
        # Update the slider value using the configured percentage
        self.driver.execute_script(
            "arguments[0].setAttribute('value', arguments[1]);", slider, slider_percentage
        )

    def _handle_confirmation_popup(self):
        try:
            confirm_selector = self.config['selectors']['confirm_popup_button']
            popup_button = WebDriverWait(self.driver, 0.1).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, confirm_selector))
            )
            popup_button.click()
        except Exception:
            pass

    def verify_and_clear_input_fields(self, order_type):
        """
        Verifies and clears both the trigger and limit price input fields.
        CSS selectors are defined in config.yaml under:
          trading.[order_type].selectors.trigger_price_field
          trading.[order_type].selectors.limit_price_field
        """
        trigger_selector = self.config['trading'][order_type]['selectors']['trigger_price_field']
        limit_selector = self.config['trading'][order_type]['selectors']['limit_price_field']
        
        trigger_element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, trigger_selector))
        )
        if trigger_element.get_attribute("value").strip() != "":
            trigger_element.clear()
        
        limit_element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, limit_selector))
        )
        if limit_element.get_attribute("value").strip() != "":
            limit_element.clear()

    def _format_price(self, price):
        """Format price to configured precision."""
        precision = self.config['trading']['price_precision']
    
        # Add this block -------------------------------------------------
        # Convert to string to analyze decimal precision
        price_str = f"{price:.20f}".rstrip('0').rstrip('.')  # Handle float imprecision
    
        if '.' in price_str:
            integer_part, decimal_part = price_str.split('.')
            decimal_places = len(decimal_part)
        
            if decimal_places > precision:
                self.logger.warning(
                    f"Price {price_str} exceeds configured precision "
                    f"({decimal_places} > {precision}). Truncating."
                )
        # End of new code ------------------------------------------------
    
        formatted_price = round(price, precision)
        self.logger.debug(f"Formatted {price} → {formatted_price}")
        return formatted_price
    
    def _input_value(self, selector, value):
        """
        Waits for an input field (by selector) and enters the given value.
        """
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        ) 
        # Clear existing value
        element.clear()
    
        # Format value before input
        formatted_value = str(self._format_price(value))
        element.send_keys(formatted_value)

    def _click_element(self, selector):
        element = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        element.click()

    def _place_ui_order(self, order_type, trigger_price, limit_price):
        """
        Place order through UI following the detailed steps.
        """
        
        try:
            btn_selector = self.config['trading'][order_type]['selectors']['button']
            self._click_element(btn_selector)

            self._select_conditional_tab(order_type)

            self.verify_and_clear_input_fields(order_type)

            trigger_selector = self.config['trading'][order_type]['selectors']['trigger_price_field']
            self._input_value(trigger_selector, str(trigger_price))

            self._select_dropdown_option(order_type)

            limit_selector = self.config['trading'][order_type]['selectors']['limit_price_field']
            self._input_value(limit_selector, str(limit_price))

            self._adjust_slider_to_full(order_type)

            submit_selector = self.config['trading'][order_type]['selectors']['place_order_button']
            self._click_element(submit_selector)

            self._handle_confirmation_popup()
            return True
        except Exception as e:
            self.logger.error(f"UI Order failed: {str(e)}")
            return False
            

    def _place_new_order(self):
        last_price = self._get_market_price()
        # Toggle order type: if last order was not 'buy', then buy; else sell.
        order_type = 'buy' if self.state.order_type != 'buy' else 'sell'
        trigger, limit = self._calculate_prices(last_price, order_type)
        
        if self._place_ui_order(order_type, trigger, limit):
            self.state.active = True
            self.state.order_type = order_type
            self.state.last_price = last_price

    def _monitor_active_order(self, order):
        """Monitor and manage existing order based on real-time price fluctuations."""
        current_price = self._get_market_price()
    
        # Add this block for immediate price reaction
        if self.state.order_type == 'buy' and current_price < self.state.last_price:
            self.logger.info("Price dropped below last price, cancelling buy order")
            self._cancel_and_replace(order)
            return
        elif self.state.order_type == 'sell' and current_price > self.state.last_price:
            self.logger.info("Price rose above last price, cancelling sell order")
            self._cancel_and_replace(order)
            return

    def _cancel_and_replace(self, order):
        """Cancel existing order and place new one with updated prices."""
        try:
            # Cancel existing order
            if self.api.cancel_order(order['id']):
                self.state.active = False
            
                # Get updated market price
                new_price = self._get_market_price()
            
                # Place new order with updated prices
                trigger, limit = self._calculate_prices(new_price, self.state.order_type)
                self._place_ui_order(self.state.order_type, trigger, limit)
            
                # Update state with new price
                self.state.last_price = new_price
                self.state.active = True
        except Exception as e:
            self.logger.error(f"Failed to cancel and replace order: {str(e)}")
            self._recover_state()
        
    def _handle_order_execution(self):
        self.logger.info("Order executed successfully")
        self.state.active = False
        self.state.order_type = 'sell' if self.state.order_type == 'buy' else 'buy'

    def _get_market_price(self):
        """
        Returns the most recent price received via the WebSocket.
        Waits briefly if no price has been received yet.
        """
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
        WebDriverWait(self.driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )


    def manage_orders(self):
        """
        Main trading loop with optional loop control.
        If 'trade_limit' is defined in config.yaml, the loop will exit after that many iterations.
        """
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
                # A short delay if needed (the WS provides continuous updates)
                time.sleep(0.1)
            except KeyboardInterrupt:
                self.logger.info("Stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error: {str(e)}")
                self._recover_state() 
