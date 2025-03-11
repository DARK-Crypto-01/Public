class TradingCore:
    # ... [other methods] ...

    def place_order_with_retry(self, order_type):
        max_retries = 5
        retry_delay = 0.1  # initial delay in seconds
        for attempt in range(max_retries):
            current_price = self._get_market_price()  # Get latest price
            trigger, limit = self._calculate_prices(current_price, order_type)
            order = self.api.place_stop_limit_order(order_type, trigger, limit)
            if order:
                self.logger.info(f"Order placed successfully on attempt {attempt+1}")
                return order
            else:
                # Extract error message from exception or response (placeholder)
                error_message = "fetch_error_from_exception()"
                if order_type == 'buy' and "trigger price must be >" in error_message:
                    self.logger.warning("Buy order failed due to trigger price issue. Retrying...")
                elif order_type == 'sell' and "trigger price must be <" in error_message:
                    self.logger.warning("Sell order failed due to trigger price issue. Retrying...")
                else:
                    self.logger.error("Order placement failed due to an unexpected error.")
                    break
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
        self.logger.error("Max retries reached. Order not placed.")
        return None

    def _place_new_order(self):
        last_price = self._get_market_price()
        order_type = self.state.order_type or 'buy'
        self.logger.info(f"Placing new {order_type} order based on last price: {last_price}")
        order = self.place_order_with_retry(order_type)
        if order:
            self.logger.info(f"New order placed: {order}")
            self.state.active = True
            self.state.order_type = order_type
            self.state.last_price = last_price
            self.state.order_id = order['id']
        else:
            self.logger.error("Failed to place new order.")

    def _cancel_and_replace(self, order):
        self.logger.info(f"Cancelling order: {order['id']} and replacing it.")
        try:
            if self.api.cancel_order(order['id']):
                self.state.active = False
                new_order = self.place_order_with_retry(self.state.order_type)
                if new_order:
                    self.logger.info(f"Replaced order successfully with new order: {new_order}")
                    self.state.last_price = self._get_market_price()
                    self.state.active = True
                    self.state.order_id = new_order['id']
                else:
                    self.logger.error("Failed to place replacement order.")
            else:
                self.logger.error("Cancellation of order failed.")
        except Exception as e:
            self.logger.error(f"Replace failed: {str(e)}")
            self._recover_state()
