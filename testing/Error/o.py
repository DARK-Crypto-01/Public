import ccxt
import pprint

# Initialize the Gate.io exchange with your API credentials
exchange = ccxt.gateio({
    'apiKey': '107b455a7a46b4e43aaf658613006a85',     # Replace with your API key
    'secret': 'a5de19e0ad40c57ad7f5d4b067747729b55a2cfbbc0f374c1b214a1cfd23f50e',      # Replace with your API secret
})

# Load market data
markets = exchange.load_markets()

# Define order parameters
symbol = 'BTC/USDT'      # The market pair
side = 'buy'             # Change to 'sell' for sell orders
order_type = 'limit'     # Using a limit order type with a stop parameter
price = 58000            # Limit price to execute once the trigger is hit (for buy)
stop_price = 57000       # The trigger price for the stop-limit order

# Define percentages for buying and selling
buy_percentage = 5       # Use 5% of available quote currency (USDT) for a buy order
sell_percentage = 10     # Use 10% of available base currency (BTC) for a sell order

# Retrieve balance from your account
balance = exchange.fetch_balance()

# Split the trading pair into base and quote currencies
base_currency = symbol.split('/')[0]   # e.g., 'BTC'
quote_currency = symbol.split('/')[1]  # e.g., 'USDT'

# Calculate the order amount based on the order side and respective percentage
if side.lower() == 'buy':
    # For a buy order, calculate the amount of BTC to buy based on available USDT balance
    available_quote = balance['free'].get(quote_currency, 0)
    # Calculate the funds to use and then determine the amount by dividing by the price
    funds_to_use = (available_quote * buy_percentage) / 100
    amount = funds_to_use / price
elif side.lower() == 'sell':
    # For a sell order, calculate the amount of BTC to sell based on available BTC balance
    available_base = balance['free'].get(base_currency, 0)
    amount = (available_base * sell_percentage) / 100
else:
    raise ValueError("Invalid side provided. Use 'buy' or 'sell'.")

# Prepare additional parameters for the stop-limit order
params = {
    'stopPrice': stop_price,  # This triggers the order when the price is reached
    # Other parameters can be added here as needed
}

try:
    # Create the order
    order = exchange.create_order(symbol, order_type, side, amount, price, params)
    pprint.pprint(order)
except Exception as e:
    print("An error occurred:", e)
