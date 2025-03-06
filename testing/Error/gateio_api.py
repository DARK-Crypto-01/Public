import ccxt

class GateIOAPIClient:
    def __init__(self, config):
        self.config = config['api']
        self.trading_config = config['trading']
        self.key = self.config['key']
        self.secret = self.config['secret']
        # Convert currency pair from "BTC_USDT" to "BTC/USDT"
        self.symbol = self.trading_config['currency_pair'].replace("_", "/")
        # Initialize the CCXT Gate.io client with rate limit enabled
        self.exchange = ccxt.gateio({
            'apiKey': self.key,
            'secret': self.secret,
            'enableRateLimit': True,
        })

    def get_open_orders(self):
        """
        Fetch all open orders for the specified currency pair using CCXT.
        """
        try:
            open_orders = self.exchange.fetch_open_orders(self.symbol)
            return open_orders
        except Exception as e:
            print(f"API Error (fetching open orders): {str(e)}")
            return []

    def cancel_order(self, order_id):
        """
        Cancel a specific order using its order ID with CCXT.
        """
        try:
            self.exchange.cancel_order(order_id, self.symbol)
            print(f"Cancelled order {order_id}.")
            return True
        except Exception as e:
            print(f"Cancel Error: {str(e)}")
            return False

    def cancel_all_orders(self, currency_pair):
        """
        Cancels all open orders for the given currency pair using CCXT.
        Returns a list of order IDs that were successfully canceled.
        """
        canceled_orders = []
        # Here, we ignore the currency_pair parameter and use the converted symbol.
        open_orders = self.get_open_orders()

        for order in open_orders:
            # CCXT returns the trading pair in the 'symbol' key.
            if order.get('symbol') == self.symbol:
                order_id = order.get('id')
                if order_id and self.cancel_order(order_id):
                    canceled_orders.append(order_id)
        
        if canceled_orders:
            print(f"All orders canceled for {self.symbol}: {canceled_orders}")
        else:
            print(f"No open orders to cancel for {self.symbol}.")
        return canceled_orders
