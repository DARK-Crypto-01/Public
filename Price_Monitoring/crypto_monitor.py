import ccxt
import pandas as pd
import yaml
import requests
import time
from datetime import datetime
import threading
import sys

class CryptoMonitor:
    def __init__(self):
        # Load configuration
        with open('config.yaml', 'r') as file:
            self.config = yaml.safe_load(file)
        
        # Initialize Gate.io API
        self.exchange = ccxt.gateio({
            'apiKey': self.config['gateio']['api_key'],
            'secret': self.config['gateio']['api_secret']
        })
        
        # Runtime control
        self.running = True
        self.first_run = True
        self.previous_top_change = set()
        self.previous_top_range = set()
        self.alert_cooldown = {}  # Cooldown tracker for alerts
        
        # Start keyboard input monitoring thread
        self.input_thread = threading.Thread(target=self.check_input, daemon=True)
        self.input_thread.start()

    def check_input(self):
        """Monitor for any keyboard input to stop the program gracefully."""
        input("Press any key + Enter to stop monitoring...\n")
        self.running = False
        print("\nStopping monitoring gracefully...")

    def get_price_data(self, symbol, timeframe='1m', limit=60):
        """Fetch OHLCV data for a symbol."""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        except ccxt.RateLimitExceeded:
            print("Rate limit hit - implementing backoff")
            time.sleep(60)
            return None
        except Exception as e:
            print(f"Error fetching data for {symbol}: {str(e)}")
            return None

    def calculate_metrics(self, df):
        """Calculate price change and range metrics."""
        if df is None or df.empty:
            return 0, 0
        
        # Vectorized calculations for better performance
        price_changes = (df['close'] - df['open']).abs().div(df['open']).sum() * 100
        price_ranges = (df['high'] - df['low']).div(df['high']).sum() * 100
        
        return price_changes, price_ranges

    def get_rankings(self):
        """Fetch and rank all spot trading symbols."""
        try:
            markets = [m for m in self.exchange.fetch_markets() if m['type'] == 'spot']
        except Exception as e:
            print(f"Error fetching markets: {str(e)}")
            return pd.DataFrame(), pd.DataFrame()
        
        rankings = []
        for market in markets:
            symbol = market['symbol']
            df = self.get_price_data(symbol)
            price_change, price_range = self.calculate_metrics(df)
            
            rankings.append({
                'symbol': symbol,
                'price_change': price_change,
                'price_range': price_range
            })

        df_rankings = pd.DataFrame(rankings)
        top_change = df_rankings.nlargest(self.config['monitoring']['top_n'], 'price_change')
        top_range = df_rankings.nlargest(self.config['monitoring']['top_n'], 'price_range')
        
        return top_change, top_range

    def send_alert(self, symbol, message):
        """Send an alert via ntfy.sh with cooldown handling."""
        if symbol in self.alert_cooldown:
            if time.time() - self.alert_cooldown[symbol] < self.config['monitoring']['alert_cooldown_seconds']:
                return
        
        try:
            requests.post(
                f"https://ntfy.sh/{self.config['notifications']['ntfy_topic']}",
                data=message.encode('utf-8'),
                headers={
                    "Title": "Crypto Alert",
                    "Priority": "urgent",
                    "Tags": "warning,skull"
                }
            )
            self.alert_cooldown[symbol] = time.time()
        except Exception as e:
            print(f"Failed to send alert: {str(e)}")

    def check_alerts(self, top_change, top_range):
        """Check for new entries/exits in top rankings and send alerts."""
        if self.first_run:
            change_threshold = self.config['monitoring']['change_alert_threshold']
            range_threshold = self.config['monitoring']['range_alert_threshold']
            self.previous_top_change = set(top_change.head(change_threshold)['symbol'])
            self.previous_top_range = set(top_range.head(range_threshold)['symbol'])
            self.first_run = False
            return

        change_threshold = self.config['monitoring']['change_alert_threshold']
        range_threshold = self.config['monitoring']['range_alert_threshold']

        current_change = set(top_change.head(change_threshold)['symbol'])
        current_range = set(top_range.head(range_threshold)['symbol'])

        new_change = current_change - self.previous_top_change
        new_range = current_range - self.previous_top_range
        exited_change = self.previous_top_change - current_change
        exited_range = self.previous_top_range - current_range

        for symbol in new_change:
            self.send_alert(symbol, f"🔥 {symbol} entered top {change_threshold} in price changes")
            
        for symbol in new_range:
            self.send_alert(symbol, f"📈 {symbol} entered top {range_threshold} in price ranges")
            
        for symbol in exited_change:
            self.send_alert(symbol, f"⬇️ {symbol} exited top {change_threshold} in price changes")
            
        for symbol in exited_range:
            self.send_alert(symbol, f"📉 {symbol} exited top {range_threshold} in price ranges")

        self.previous_top_change = current_change
        self.previous_top_range = current_range

    def run(self):
        """Main monitoring loop."""
        iteration = 0
        max_iterations = self.config['monitoring'].get('max_iterations', 0)
        
        try:
            while self.running:
                if max_iterations > 0 and iteration >= max_iterations:
                    print("Reached maximum iterations. Stopping...")
                    break
                
                print(f"\n{datetime.now().isoformat()} - Iteration {iteration+1}")
                print(f"{'Infinite mode' if max_iterations == 0 else f'Iteration {iteration+1}/{max_iterations}'}")
                
                try:
                    top_change, top_range = self.get_rankings()
                    
                    print("\nTop Price Changes:")
                    print(top_change[['symbol', 'price_change']].head(25).to_string(index=False))
                    print("\nTop Price Ranges:")
                    print(top_range[['symbol', 'price_range']].head(25).to_string(index=False))
                    
                    self.check_alerts(top_change, top_range)
                    
                    if not self.running:
                        break
                        
                    sleep_time = self.config['monitoring']['update_frequency_seconds']
                    print(f"\nSleeping for {sleep_time} seconds...")
                    
                    # Break sleep into smaller chunks for responsive stopping
                    for _ in range(sleep_time):
                        if not self.running:
                            break
                        time.sleep(1)
                    
                    iteration += 1
                    
                except Exception as e:
                    print(f"Error in iteration: {str(e)}")
                    if not self.running:
                        break
                    time.sleep(10)
                    
        except Exception as e:
            print(f"Critical error: {str(e)}")
        finally:
            print("Monitoring stopped")

if __name__ == "__main__":
    monitor = CryptoMonitor()
    monitor.run()
