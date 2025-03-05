# gateio_api.py
import ccxt
import logging
from typing import List, Dict, Optional

class GateIOAPIClient:
    def __init__(self, config: dict):
        """
        Initialize CCXT-based Gate.io client
        :param config: Configuration dictionary from YAML
        """
        self.logger = logging.getLogger("GateIOAPIClient")
        self.config = config
        self._validate_config()
        
        # Initialize CCXT exchange
        self.exchange = ccxt.gateio({
            'apiKey': config['api']['key'],
            'secret': config['api']['secret'],
            'enableRateLimit': True,  # Essential for rate limit compliance
            'options': {
                'adjustForTimeDifference': True,  # Auto-sync time difference
                'createMarketBuyOrderRequiresPrice': False,
            }
        })
        self.currency_pair = config['trading']['currency_pair']

    def _validate_config(self):
        """Validate required configuration parameters"""
        required_keys = ['key', 'secret', 'endpoints']
        if not all(k in self.config['api'] for k in required_keys):
            raise ValueError("Missing required API configuration parameters")

    def get_open_orders(self) -> List[Dict]:
        """
        Get all open orders for the configured currency pair
        :return: List of open orders
        """
        try:
            return self.exchange.fetch_open_orders(self.currency_pair)
        except ccxt.NetworkError as e:
            self.logger.error(f"Network error fetching orders: {str(e)}")
            return []
        except ccxt.ExchangeError as e:
            self.logger.error(f"Exchange error fetching orders: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order by ID
        :param order_id: Order ID to cancel
        :return: True if successful, False otherwise
        """
        try:
            response = self.exchange.cancel_order(order_id, self.currency_pair)
            return response.get('status') in ['closed', 'canceled']
        except ccxt.OrderNotFound:
            self.logger.warning(f"Order {order_id} not found")
            return True  # Consider already canceled
        except ccxt.NetworkError as e:
            self.logger.error(f"Network error canceling order: {str(e)}")
            return False
        except ccxt.ExchangeError as e:
            self.logger.error(f"Exchange error canceling order: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            return False

    def cancel_all_orders(self, currency_pair: Optional[str] = None) -> List[str]:
        """
        Cancel all open orders for a currency pair
        :param currency_pair: Optional currency pair (uses config pair if None)
        :return: List of canceled order IDs
        """
        canceled_ids = []
        target_pair = currency_pair or self.currency_pair
        
        try:
            # CCXT's native method for canceling all orders
            response = self.exchange.cancel_all_orders(target_pair)
            if isinstance(response, list):
                canceled_ids = [order['id'] for order in response]
        except ccxt.NotSupported:
            # Fallback to manual cancellation if not supported
            self.logger.warning("Using manual order cancellation fallback")
            orders = self.get_open_orders()
            for order in orders:
                if order['symbol'] == target_pair:
                    if self.cancel_order(order['id']):
                        canceled_ids.append(order['id'])
        except Exception as e:
            self.logger.error(f"Error canceling all orders: {str(e)}")
            
        return canceled_ids
