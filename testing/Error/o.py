import ccxt
import pprint

# Initialize the Gate.io exchange with your API credentials
exchange = ccxt.gateio({
    'apiKey': '107b455a7a46b4e43aaf658613006a85',     # Replace with your API key
    'secret': 'a5de19e0ad40c57ad7f5d4b067747729b55a2cfbbc0f374c1b214a1cfd23f50e',      # Replace with your API secret
    'enableRateLimit': True,
})

# Load market data
markets = exchange.load_markets()

# Define order parameters
symbol = 'BTC/USDT'      # The market pair
side = 'buy'            # 'buy' or 'sell'
order_type = 'limit'     # Using a limit order type with a stop parameter
amount = 0.000012           # Order size
price = 100000            # Limit price to execute once the trigger is hit
stop_price = 99990       # The trigger price for the stop-limit order

# The parameters here instruct Gate.io to treat this as a stop-limit order.
params = {
    'stopPrice': stop_price,  # This is the price at which the order is triggered
    # Additional params such as 'timeInForce' may be added if required
}

try:
    # Create the order
    order = exchange.create_order(symbol, order_type, side, amount, price, params)
    pprint.pprint(order)
except Exception as e:
    print("An error occurred:", e)
