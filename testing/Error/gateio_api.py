import requests
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode
# Add at the top with other imports
from urllib.parse import urlencode

class GateIOAPIClient:
    def __init__(self, config):
        self.config = config['api']
        self.trading_config = config['trading']
        self.base_url = self.config['base_url']
        self.key = self.config['key']
        self.secret = self.config['secret']

    def _generate_signature(self, method, endpoint, query_string=None, payload=None):
        timestamp = str(time.time())
        path = endpoint.split('?')[0]  # Extract path without query params
    
        body = json.dumps(payload) if payload else ''
        body_hash = hashlib.sha512(body.encode()).hexdigest()
    
        # Verified signature format from Gate.io docs
        signature_string = "\n".join([
            method.upper(),
            path,
            query_string or '',
            body_hash,
            timestamp
        ])

        signature = hmac.new(
            self.secret.encode('utf-8'),
            signature_string.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()

        return {
            "KEY": self.key,
            "Timestamp": timestamp,
            "SIGN": signature,
            "Content-Type": "application/json" if method in ['POST', 'PUT', 'DELETE'] else ""
        }

    def get_open_orders(self):
        endpoint = self.config['endpoints']['open_orders']
        query = urlencode({
            'currency_pair': self.trading_config['currency_pair'],
            'status': 'open'
        })
        url = f"{self.base_url}{endpoint}?{query}"
        headers = self._generate_signature('GET', endpoint, query)

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API Error: {str(e)}")
            return []

    def cancel_order(self, order_id):
        endpoint = self.config['endpoints']['cancel_order'].format(order_id=order_id)
        url = f"{self.base_url}{endpoint}"
        headers = self._generate_signature('DELETE', endpoint)

        try:
            response = requests.delete(url, headers=headers)
            return response.status_code == 204
        except Exception as e:
            print(f"Cancel Error: {str(e)}")
            return False

    def cancel_all_orders(self, currency_pair):
        """
        Cancels all open orders for the given currency pair.
        Returns a list of order IDs that were successfully canceled.
        """
        canceled_orders = []
        open_orders = self.get_open_orders()
        for order in open_orders:
            # Ensure the order belongs to the specified currency pair
            if order.get('currency_pair') == currency_pair:
                order_id = order.get('id')
                if order_id and self.cancel_order(order_id):
                    canceled_orders.append(order_id)
        return canceled_orders
