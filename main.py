from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from trading_bot import TradingBot
import yaml
import logging
import sys
import os

def get_default_profile_path(browser_name):
    """Get the default profile path based on the operating system and browser."""
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
    return paths.get(browser_name, {}).get(system, '')

def load_config():
    try:
        with open('config.yaml', 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

def setup_browser(browser_name):
    try:
        # Get profile path from config or use default
        config = load_config()
        profile_path = config['browser'].get('profile_path', get_default_profile_path(browser_name.lower()))
        
        if browser_name.lower() == 'chrome':
            options = webdriver.ChromeOptions()
            options.add_argument(f'--user-data-dir={profile_path}')
            options.add_argument('--profile-directory=Default')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            service = ChromeService(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=options)
            
        elif browser_name.lower() == 'firefox':
            options = webdriver.FirefoxOptions()
            if os.path.exists(profile_path):
                # Find the default profile directory
                profile_dirs = [d for d in os.listdir(profile_path) if d.endswith('.default')]
                if profile_dirs:
                    profile_path = os.path.join(profile_path, profile_dirs[0])
            options.add_argument(f'-profile {profile_path}')
            service = FirefoxService(GeckoDriverManager().install())
            return webdriver.Firefox(service=service, options=options)
            
        elif browser_name.lower() == 'edge':
            options = webdriver.EdgeOptions()
            options.add_argument(f'--user-data-dir={profile_path}')
            options.add_argument('--profile-directory=Default')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            service = EdgeService(EdgeChromiumDriverManager().install())
            return webdriver.Edge(service=service, options=options)
            
        else:
            raise ValueError(f"Unsupported browser: {browser_name}")
            
    except Exception as e:
        print(f"Error setting up browser: {e}")
        logging.error(f"Browser setup error: {e}")
        sys.exit(1)

def main():
    config = load_config()
    
    logging.basicConfig(
        filename=config['logging']['file'],
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    driver = None
    try:
        browser_name = config['browser']['name']
        driver = setup_browser(browser_name)
        driver.maximize_window()
        
        bot = TradingBot(driver)
        bot.start_trading()
        
    except KeyboardInterrupt:
        logging.info("Trading bot stopped by user")
        print("\nTrading bot stopped by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print(f"An error occurred: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

if __name__ == "__main__":
    main()
