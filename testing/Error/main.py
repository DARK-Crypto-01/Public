def main():
    config = load_config()
    setup_logging(config['logging'])

    try:
        trader = TradingCore(config)  
        trader.manage_orders()
    except KeyboardInterrupt:
        logging.info("Stopped by user")
    except Exception as e:
        logging.critical(f"Fatal error: {str(e)}")
    finally:
        logging.info("Trading session ended")
