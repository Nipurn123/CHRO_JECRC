from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import os
import random
import csv
from dotenv import load_dotenv
import undetected_chromedriver as uc
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_chrome_version():
    """Get the installed Chrome version"""
    try:
        # For macOS
        import subprocess
        process = subprocess.Popen(
            ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'],
            stdout=subprocess.PIPE
        )
        version = process.communicate()[0].decode('UTF-8').replace('Google Chrome ', '').strip()
        return int(version.split('.')[0])
    except:
        return 133  # Default to latest version if can't detect

def setup_driver():
    """Setup and return the Chrome driver with appropriate options"""
    options = uc.ChromeOptions()
    
    # Remove headless mode and add debugging options
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument("--window-size=1920,1080")
    
    # Add random user agent
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
    ]
    options.add_argument(f'user-agent={user_agents[0]}')  # Use stable MacOS agent
    
    chrome_version = get_chrome_version()
    print(f"Detected Chrome version: {chrome_version}")
    
    try:
        driver = uc.Chrome(
            options=options,
            version_main=chrome_version
        )
        driver.set_page_load_timeout(30)
        print("Driver initialized successfully")
        return driver
    except Exception as e:
        logger.error(f"Error with specific version, trying default: {str(e)}")
        return uc.Chrome(options=options)

def wait_for_response(driver, timeout=60):
    """Wait for and extract the response from Perplexity"""
    try:
        wait = WebDriverWait(driver, timeout)
        
        # Wait for the loading indicator to disappear with shorter timeout
        try:
            wait_loading = WebDriverWait(driver, 30)  # Shorter timeout for loading indicator
            wait_loading.until_not(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'animate-pulse')]"))
            )
        except Exception as e:
            logger.warning(f"Loading indicator not found or didn't disappear: {str(e)}")
            # Continue anyway - the response might still be available
        
        # Try different selectors for the response with a shorter timeout
        response_selectors = [
            "//div[contains(@class, 'prose')]//p",
            "//div[contains(@class, 'markdown-content')]//p",
            "//div[contains(@class, 'response')]//p",
            "//div[contains(@class, 'answer-content')]//p"
        ]
        
        response_text = ""
        for selector in response_selectors:
            try:
                # Use a shorter timeout for each selector attempt
                wait_response = WebDriverWait(driver, 15)
                elements = wait_response.until(
                    EC.presence_of_all_elements_located((By.XPATH, selector))
                )
                response_text = "\n".join([elem.text for elem in elements if elem.text.strip()])
                if response_text:
                    logger.info(f"Found response with selector: {selector}")
                    break
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {str(e)}")
                continue
        
        # If no text found, try a more general approach
        if not response_text:
            logger.warning("No response found with specific selectors, trying fallback approach")
            try:
                # Just get any text from the main content area
                main_content = driver.find_element(By.XPATH, "//main")
                response_text = main_content.text
            except:
                pass
        
        # If still no response, take a screenshot if possible (for debugging)
        if not response_text:
            try:
                screenshot_path = f"perplexity_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                driver.save_screenshot(screenshot_path)
                logger.warning(f"No response found. Screenshot saved to {screenshot_path}")
            except:
                pass
            
            # Return a failure message
            return "Failed to extract response from Perplexity"
        
        return response_text.strip()
        
    except Exception as e:
        logger.error(f"Error getting response: {str(e)}")
        return f"Error: {str(e)}"

def send_prompt(driver, prompt):
    """Send prompt to Perplexity"""
    try:
        print("\nAttempting to send prompt...")
        time.sleep(2)
        
        # Wait for textarea to be present and clickable
        wait = WebDriverWait(driver, 20)
        
        # Try multiple selectors for the textarea
        textarea_selectors = [
            "//textarea[contains(@class, 'overflow-auto')]",
            "//textarea[@placeholder='Ask anything...']",
            "//div[contains(@class, 'bg-background')]//textarea",
            "//textarea"
        ]
        
        textarea = None
        for selector in textarea_selectors:
            try:
                textarea = wait.until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                if textarea:
                    break
            except:
                continue
        
        if not textarea:
            return False
        
        # Click and input text
        try:
            textarea.click()
        except:
            driver.execute_script("arguments[0].click();", textarea)
        
        time.sleep(1)
        textarea.clear()
        textarea.send_keys(prompt)
        time.sleep(1)
        
        # Submit the prompt
        submit_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Submit']"))
        )
        
        if not submit_button.is_enabled():
            return False
            
        submit_button.click()
        print("Prompt sent successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error sending prompt: {str(e)}")
        return False

def read_companies():
    """Read companies from CSV file"""
    companies = []
    try:
        with open('top100.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                companies.append(row['Company Name'].strip())
    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")
        return []
    return companies

def save_results(results):
    """Save results to CSV file"""
    filename = 'perplexity_results.csv'
    
    try:
        # Check if file exists to determine if we need to write headers
        file_exists = os.path.isfile(filename)
        
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['Company', 'Prompt', 'Response', 'Timestamp'])
            # Write header only if file is being created for the first time
            if not file_exists:
                writer.writeheader()
            # Write only the latest result instead of all results
            if results:
                writer.writerow(results[-1])  # Write only the last result
        print(f"\nResult appended to {filename}")
    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")

def main():
    driver = setup_driver()
    companies = read_companies()
    results = []
    
    if not companies:
        print("No companies found in CSV file")
        driver.quit()
        return
    
    try:
        # Navigate to Perplexity
        print("\nNavigating to Perplexity...")
        driver.get("https://www.perplexity.ai/")
        time.sleep(5)
        
        # Process each company
        for i, company in enumerate(companies, 1):
            print(f"\nProcessing company {i}/100: {company}")
            
            prompt = f"""Provide the full name of the Chief Human Resources Officer (CHRO) of {company}, based in India, as of February 23, 2025. Ensure the response pertains exclusively to {company} and no other entity or region. Respond with only the full name, nothing else. Also give the LinkedIn URL."""
            
            if send_prompt(driver, prompt):
                # Wait for and capture the response
                response = wait_for_response(driver)
                
                # Store the result
                results.append({
                    'Company': company,
                    'Prompt': prompt,
                    'Response': response,
                    'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                
                print(f"Response received: {response}")
                print(f"Waiting 3 seconds before next company...")
                time.sleep(3)
            else:
                print(f"Failed to send prompt for {company}, refreshing page...")
                driver.refresh()
                time.sleep(5)
                
                # Store the failed attempt
                results.append({
                    'Company': company,
                    'Prompt': prompt,
                    'Response': 'FAILED',
                    'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            
            # Save results after each company (in case of crashes)
            save_results(results)
            
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        
    finally:
        # Save final results
        save_results(results)
        input("Press Enter to close the browser...")
        driver.quit()

if __name__ == "__main__":
    main()
