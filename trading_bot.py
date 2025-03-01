import yaml
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
import logging
import locale

class TradingBot:
    def __init__(self, driver):
        self.driver = driver
        self.config = self.load_config()
        self.setup_logging()

    def load_config(self):
        with open('config.yaml', 'r') as file:
            return yaml.safe_load(file)

    def setup_logging(self):
        logging.basicConfig(
            filename=self.config['logging']['file'],
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def find_element(self, selector):
        return WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

    def click_element(self, selector):
        element = self.find_element(selector)
        element.click()

    def input_text(self, selector, text):
        element = self.find_element(selector)
        element.clear()
        element.send_keys(str(text))

    def get_current_price(self):
        locale.setlocale(locale.LC_ALL, '')
        price_element = self.find_element(self.config['selectors']['price'])
        return locale.atof(price_element.text)

    def calculate_prices(self, current_price, is_buy=True):
        action = 'buy' if is_buy else 'sell'
        trigger_adjust = self.config['trading'][action]['trigger_price_adjust']
        limit_adjust = self.config['trading'][action]['limit_price_adjust']
        
        if is_buy:
            trigger_price = current_price * (1 + trigger_adjust/100)
            limit_price = current_price * (1 + limit_adjust/100)
        else:
            trigger_price = current_price * (1 - trigger_adjust/100)
            limit_price = current_price * (1 - limit_adjust/100)
            
        return round(trigger_price, 2), round(limit_price, 2)

    def place_buy_order(self, current_price):
        try:
            selectors = self.config['trading']['buy']['selectors']
            trigger_price, limit_price = self.calculate_prices(current_price, is_buy=True)

            # Click buy button
            self.click_element(selectors['button'])
            
            # Select conditional tab
            self.click_element(selectors['conditional_tab'])
            
            # Set trigger price
            self.input_text(selectors['trigger_price_field'], trigger_price)
            
            # Set condition to greater than or equal
            self.click_element(selectors['condition_dropdown'])
            self.click_element(selectors['greater_equal_option'])
            
            # Set limit price
            self.input_text(selectors['limit_price_field'], limit_price)
            
            # Set amount (slide to 100%)
            self.click_element(selectors['amount_slider'])
            
            # Place order
            self.click_element(selectors['place_order_button'])
            
            # Confirm order
            self.click_element(self.config['selectors']['confirm_popup_button'])
            
            logging.info(f"Buy order placed - Trigger: {trigger_price}, Limit: {limit_price}")
            return True

        except WebDriverException as e:
            logging.error(f"Error placing buy order: {str(e)}")
            return False

    def place_sell_order(self, current_price):
        try:
            selectors = self.config['trading']['sell']['selectors']
            trigger_price, limit_price = self.calculate_prices(current_price, is_buy=False)

            # Click sell button
            self.click_element(selectors['button'])
            
            # Select conditional tab
            self.click_element(selectors['conditional_tab'])
            
            # Set trigger price
            self.input_text(selectors['trigger_price_field'], trigger_price)
            
            # Set condition to less than or equal
            self.click_element(selectors['condition_dropdown'])
            self.click_element(selectors['less_equal_option'])
            
            # Set limit price
            self.input_text(selectors['limit_price_field'], limit_price)
            
            # Set amount (slide to 100%)
            self.click_element(selectors['amount_slider'])
            
            # Place order
            self.click_element(selectors['place_order_button'])
            
            # Confirm order
            self.click_element(self.config['selectors']['confirm_popup_button'])
            
            logging.info(f"Sell order placed - Trigger: {trigger_price}, Limit: {limit_price}")
            return True

        except WebDriverException as e:
            logging.error(f"Error placing sell order: {str(e)}")
            return False

    def cancel_all_orders(self):
        try:
            orders = self.driver.find_elements(By.CSS_SELECTOR, self.config['selectors']['stop_limit_orders'])
            for order in orders:
                cancel_button = order.find_element(By.CSS_SELECTOR, self.config['selectors']['cancel_order_button'])
                cancel_button.click()
                self.click_element(self.config['selectors']['confirm_popup_button'])
            logging.info("All orders cancelled successfully")
            return True
        except WebDriverException as e:
            logging.error(f"Error cancelling orders: {str(e)}")
            return False

    def start_trading(self):
        try:
            self.driver.get(self.config['trading']['url'])
            # Wait 30 seconds for page to fully load
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.config['selectors']['price']))
            )
            logging.info("Page fully loaded after initial wait")
            
            loops = 0
            max_loops = self.config['trading']['max_loops']

            while max_loops is None or loops < max_loops:
                current_price = self.get_current_price()
                logging.info(f"Current price: {current_price}")

                # Cancel existing orders
                self.cancel_all_orders()

                # Place new orders
                self.place_buy_order(current_price)
                self.place_sell_order(current_price)

                loops += 1
                logging.info(f"Completed trading loop {loops}")

        except Exception as e:
            logging.error(f"Trading error: {str(e)}")
            raise
