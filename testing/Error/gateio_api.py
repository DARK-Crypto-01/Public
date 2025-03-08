import ccxt

class GateIOAPIClient:
    def __init__(self, config):
        self.config = config['api']
        self.trading_config = config['trading']
        self.key = self.config['key']
        self.secret = self.config['secret']
        self.base_url = self.config['base_url']
        # Convert currency pair from "BTC_USDT" to "BTC/USDT"
        self.symbol = self.trading_config['currency_pair'].replace("_", "/")
        # Initialize the CCXT Gate.io client with rate limit enabled
        self.exchange = ccxt.gateio({
            'apiKey': self.key,
            'secret': self.secret,
            'enableRateLimit': True,
        })
        self.logger = logging.getLogger("GateIOAPIClient")

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

    # gateio_api.py (Updated)
    def calculate_order_amount(self, side, limit_price):
        """Calculate base currency amount with proper conversion"""
        balance = self.exchange.fetch_balance()
        base, quote = self.symbol.split('/')
    
        try:
            if side == 'buy':
                # Get percentage from buy config
                buy_pct = self.config['trading']['buy']['amount_percentage']
                available_quote = balance[quote]['free']
            
                # Calculate quote amount and convert to base
                quote_amount = (available_quote * buy_pct) / 100
                return quote_amount / limit_price  # Base currency amount
            
            elif side == 'sell':
                # Direct percentage of base currency
                sell_pct = self.config['trading']['sell']['amount_percentage']
                available_base = balance[base]['free']
                return (available_base * sell_pct) / 100
            
            raise ValueError("Invalid side specified")
        
        except KeyError as e:
            self.logger.error(f"Balance check failed: {str(e)}")
            return 0
        except ZeroDivisionError:
            self.logger.error("Invalid zero price encountered")
            return 0

    def place_stop_limit_order(self, order_type, trigger_price, limit_price):
        try:
            # Get amount in base currency terms
            amount = self.calculate_order_amount(order_type, limit_price)
            if amount <= 0:
                self.logger.error("Invalid order amount calculated")
                return None

            # Gate.io requires base amount in minimum increments
            market = self.exchange.market(self.symbol)
            precision = market['precision']['amount']
            amount = self.exchange.amount_to_precision(self.symbol, amount)

            params = {
                'stopPrice': trigger_price,
                'type': 'limit',
                'price': limit_price,
                'amount': amount
            }

            order = self.exchange.create_order(
                symbol=self.symbol,
                type='limit',
                side=order_type,
                amount=amount,
                price=limit_price,
                params=params
            )
        
            return order
         
        except Exception as e:
            self.logger.error(f"Order failed: {str(e)}")
            return None
