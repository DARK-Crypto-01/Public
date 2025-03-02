import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Geckodriver setup instructions for Ubuntu:
# 1. Download latest geckodriver from https://github.com/mozilla/geckodriver/releases
# 2. Extract: tar -xvzf geckodriver-*
# 3. Move to /usr/local/bin: sudo mv geckodriver /usr/local/bin/
# 4. Verify with: geckodriver --version

def main():
    # Configure Firefox profile
    firefox_profile_path = "/home/darkcrypto1992/.mozilla/firefox/85i3p67u.Test"
    
    options = Options()
    options.add_argument("-profile")
    options.add_argument(firefox_profile_path)
    
    # Initialize driver
    driver = webdriver.Firefox(options=options)
    
    try:
        # Navigate to URL and wait
        driver.get("http://www.url.com")
        time.sleep(30)  # Wait for page to load
        
        # Click first element
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "div.sc-3acc2a25-0:nth-child(1)")
        )).click()
        
        # Click tab element
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "#mantine-r58-tab-stopByConditional > div:nth-child(1) > span:nth-child(1)")
        )).click()
        
        # Enter 2000 in input field
        input_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, ".tr-m-0 > div:nth-child(2) > input:nth-child(1)")
        ))
        input_field.clear()
        input_field.send_keys("2000")
        
        # Click dropdown
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "div.fw-500")
        )).click()
        
        # Select dropdown item
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, ".mantine-1ufzw1b > span:nth-child(1)")
        )).click()
        
        # Enter 1000 in second input field
        second_input = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "div.row-container:nth-child(3) > div:nth-child(1) > div:nth-child(2) > input:nth-child(1)")
        ))
        second_input.clear()
        second_input.send_keys("1000")
        
        # Adjust slider using JavaScript
        slider = WebDriverWait(driver, 20).until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, ".mantine-GateSlider-thumb")
        ))
        driver.execute_script(
            "arguments[0].setAttribute('value', '100');", slider
        )
        
        # Click final button
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, ".mantine-cwyisp")
        )).click()
        
        # Check for popup and handle if present
        try:
            popup_button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.mantine-132odz5:nth-child(2) > div:nth-child(1)")
            ))
            popup_button.click()
            print("Popup detected and closed")
        except:
            print("No popup detected")
        
        # Add final delay to observe results
        time.sleep(5)
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
