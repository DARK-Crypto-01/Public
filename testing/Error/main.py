import logging
import sys
import yaml
from trading_bot import TradingCore

def load_config():
    """Load configuration from YAML file"""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.critical(f"Config loading error: {str(e)}")
        sys.exit(1)

def setup_logging(log_config):
    """Configure logging based on config.yaml"""
    handlers = []
    if log_config.get('enabled', True):
        handlers.append(logging.FileHandler(log_config.get('file', 'trading_bot.log')))
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=log_config.get('level', 'INFO'),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def main():
    config = load_config()
    setup_logging(config['logging'])
    logging.info("Starting trading bot")

    try:
        # Instantiate TradingCore with config (driver removed for API-only orders)
        trader = TradingCore(config)
        trader.manage_orders()
    except KeyboardInterrupt:
        logging.info("Stopped by user")
    except Exception as e:
        logging.critical(f"Fatal error: {str(e)}")
    finally:
        logging.info("Trading session ended")

if __name__ == "__main__":
    main()
