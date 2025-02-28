from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from trading_bot import TradingCore
import yaml
import logging
import sys
import os

def get_default_profile_path(browser_name):
    """Get default browser profile path based on OS"""
    home = os.path.expanduser('~')
    paths = {
        'chrome': {
            'windows': os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data'),
            'darwin': os.path.join(home, 'Library', 'Application Support', 'Google', 'Chrome'),
            'linux': os.path.join(home, '.config', 'google-chrome')
        },
        'firefox': {
            'windows': os.path.join(os.environ.get('APPDATA', ''), 'Mozilla', 'Firefox', 'Profiles'),
            'darwin': os.path.join(home, 'Library', 'Application Support', 'Firefox', 'Profiles'),
            'linux': os.path.join(home, '.mozilla', 'firefox')
        },
        'edge': {
            'windows': os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Edge', 'User Data'),
            'darwin': os.path.join(home, 'Library', 'Application Support', 'Microsoft Edge'),
            'linux': os.path.join(home, '.config', 'microsoft-edge')
        }
    }
    
    system = 'darwin' if sys.platform == 'darwin' else 'windows' if sys.platform == 'win32' else 'linux'
    return paths.get(browser_name.lower(), {}).get(system, '')

def load_config():
    """Load configuration from YAML file"""
    try:
        with open('config.yaml') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.critical(f"Config loading error: {str(e)}")
        sys.exit(1)

def setup_logging(config):
    """Configure logging system using the entire configuration"""
    logging.basicConfig(
        level=config['logging']['level'],
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config['logging']['file']),
            logging.StreamHandler()
        ]
    )

def setup_browser(config):
    """Initialize browser driver with OS-specific settings"""
    try:
        browser_name = config['browser']['name'].lower()
        profile_path = config['browser'].get('profile_path') or get_default_profile_path(browser_name)
        
        if browser_name == 'chrome':
            options = webdriver.ChromeOptions()
            service = ChromeService(ChromeDriverManager().install())
            options.add_argument(f"--user-data-dir={profile_path}")
            options.add_argument("--profile-directory=Default")

        elif browser_name == 'firefox':
            options = webdriver.FirefoxOptions()
            service = FirefoxService(GeckoDriverManager().install())
            if os.path.exists(profile_path):
                profile_dirs = [d for d in os.listdir(profile_path) if d.endswith('.default')]
                if profile_dirs:
                    profile_path = os.path.join(profile_path, profile_dirs[0])
            options.add_argument(f"-profile {profile_path}")

        elif browser_name == 'edge':
            options = webdriver.EdgeOptions()
            service = EdgeService(EdgeChromiumDriverManager().install())
            options.add_argument(f"--user-data-dir={profile_path}")
            options.add_argument("--profile-directory=Default")

        else:
            raise ValueError(f"Unsupported browser: {browser_name}")

        # Common options for all browsers
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Initialize driver
        driver = getattr(webdriver, browser_name.capitalize())(service=service, options=options)
        driver.maximize_window()
        return driver

    except Exception as e:
        logging.critical(f"Browser setup failed: {str(e)}")
        sys.exit(1)

def main():
    config = load_config()
    # Pass the entire configuration to setup_logging
    setup_logging(config)
    
    driver = None
    try:
        driver = setup_browser(config)
        driver.get(config['trading']['url'])
        
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        trader = TradingCore(driver, config)
        trader.manage_orders()

    except KeyboardInterrupt:
        logging.info("Stopped by user")
    except Exception as e:
        logging.critical(f"Fatal error: {str(e)}")
    finally:
        if driver:
            driver.quit()
        sys.exit()

if __name__ == "__main__":
    main()
