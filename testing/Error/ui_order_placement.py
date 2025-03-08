# ui_order_placement.py

import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class UIOrderPlacement:
    def __init__(self, driver, config):
        self.driver = driver
        self.config = config

    def _click_element(self, selector):
        element = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        element.click()

    def _input_value(self, selector, value, precision):
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        element.clear()
        formatted_value = f"{float(value):.{precision}f}"
        element.send_keys(formatted_value)

    def verify_and_clear_input_fields(self, order_type):
        trigger_selector = self.config['trading'][order_type]['selectors']['trigger_price_field']
        limit_selector = self.config['trading'][order_type]['selectors']['limit_price_field']
        for selector in [trigger_selector, limit_selector]:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            if element.get_attribute("value").strip() != "":
                element.clear()

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

    def place_ui_order(self, order_type, trigger_price, limit_price):
        """
        Place an order via the UI. Returns True if successful, False otherwise.
        """
        try:
            # Click the corresponding order button (buy or sell)
            btn_selector = self.config['trading'][order_type]['selectors']['button']
            self._click_element(btn_selector)

            # Select the conditional order tab
            self._select_conditional_tab(order_type)

            # Clear previous inputs
            self.verify_and_clear_input_fields(order_type)

            # Input trigger price
            trigger_selector = self.config['trading'][order_type]['selectors']['trigger_price_field']
            precision = self.config['trading']['price_precision']
            self._input_value(trigger_selector, trigger_price, precision)

            # Select dropdown option for condition
            self._select_dropdown_option(order_type)

            # Input limit price
            limit_selector = self.config['trading'][order_type]['selectors']['limit_price_field']
            self._input_value(limit_selector, limit_price, precision)

            # Adjust the slider
            self._adjust_slider_to_full(order_type)

            # Click the place order button
            submit_selector = self.config['trading'][order_type]['selectors']['place_order_button']
            self._click_element(submit_selector)

            # Handle any confirmation popup
            self._handle_confirmation_popup()

            return True
        except Exception as e:
            logging.getLogger("UIOrderPlacement").error(f"UI Order failed: {str(e)}")
            return False
