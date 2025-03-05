import requests
import hashlib
import hmac
import json
import time
from urllib.parse import urlparse, urlencode

class GateIOAPIClient:
    def __init__(self, config):
        self.config = config['api']
        self.trading_config = config['trading']
        self.base_url = self.config['base_url']
        self.key = self.config['key']
        self.secret = self.config['secret'].encode('utf-8')
        self.base_path = urlparse(self.base_url).path  # Extract /api/v4 from base URL

    def _generate_signature(self, method, endpoint, query_string=None, payload=None):
        # Combine base path with endpoint path
        full_path = f"{self.base_path.rstrip('/')}/{endpoint.lstrip('/')}".split('?')[0]
        
        # Convert timestamp to integer
        timestamp = str(int(time.time()))
        
        # Sort query parameters alphabetically
        if query_string:
            params = sorted(query_string.split('&'))
            query_string = '&'.join(params)
        
        # Generate SHA512 hash of request body
        body = json.dumps(payload) if payload else ''
        body_hash = hashlib.sha512(body.encode()).hexdigest()
        
        # Create signature payload
        signature_payload = '\n'.join([
            method.upper(),
            full_path,
            query_string or '',
            body_hash,
            timestamp
        ])
        
        # Generate HMAC-SHA512 signature
        signature = hmac.new(
            self.secret,
            signature_payload.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        # Construct headers
        headers = {
            "KEY": self.key,
            "Timestamp": timestamp,
            "SIGN": signature
        }
        
        # Add Content-Type only for methods with body
        if method in ['POST', 'PUT', 'DELETE']:
            headers["Content-Type"] = "application/json"
            
        return headers

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
        except requests.exceptions.HTTPError as e:
            print(f"API Error: {e.response.text}")
            return []
        except Exception as e:
            print(f"Request Failed: {str(e)}")
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
