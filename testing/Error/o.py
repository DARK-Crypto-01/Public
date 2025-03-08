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
side = 'sell'            # 'buy' or 'sell'
order_type = 'limit'     # Using a limit order type with a stop parameter
price = 1000            # Limit price to execute once the trigger is hit
stop_price = 2000       # The trigger price for the stop-limit order
percentage = 100          # Percentage of the balance to use (e.g., 10% of your balance)

# Retrieve balance
balance = exchange.fetch_balance()

# For example, we're using USDT as the quote currency. Change as per your symbol
base_currency = symbol.split('/')[0]  # e.g., 'BTC'
quote_currency = symbol.split('/')[1]  # e.g., 'USDT'

# Get the available balance of the quote currency (e.g., USDT)
available_balance = balance['free'][quote_currency]

# Calculate the order amount based on the percentage of the available balance
amount = (available_balance * percentage) / 100

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
