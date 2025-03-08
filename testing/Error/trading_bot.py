import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from gateio_api import GateIOAPIClient
from gateio_websocket import GateIOWebSocketClient

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

        # Initialize WebSocket client with proper credentials from the new module
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
        slider_percentage = self.config["trading"]["slider_percentage"]
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
        precision = self.config['trading']['price_precision']
        price_str = f"{price:.20f}".rstrip('0').rstrip('.')
        if '.' in price_str:
            integer_part, decimal_part = price_str.split('.')
            decimal_places = len(decimal_part)
            if decimal_places > precision:
                self.logger.warning(
                    f"Price {price_str} exceeds configured precision "
                    f"({decimal_places} > {precision}). Truncating."
                )
        formatted_price = round(price, precision)
        self.logger.debug(f"Formatted {price} → {formatted_price}")
        return formatted_price

    def _input_value(self, selector, value):
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        element.clear()
        formatted_value = str(self._format_price(value))
        element.send_keys(formatted_value)

    def _click_element(self, selector):
        element = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        element.click()

    def _place_ui_order(self, order_type, trigger_price, limit_price):
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
        order_type = 'buy' if self.state.order_type != 'buy' else 'sell'
        trigger, limit = self._calculate_prices(last_price, order_type)
        if self._place_ui_order(order_type, trigger, limit):
            self.state.active = True
            self.state.order_type = order_type
            self.state.last_price = last_price

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
                self._place_ui_order(self.state.order_type, trigger, limit)
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
