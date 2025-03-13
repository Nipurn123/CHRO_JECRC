from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import os
import random
import csv
import re
import json
from dotenv import load_dotenv
import undetected_chromedriver as uc
import logging
from datetime import datetime
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_chrome_version():
    """Get the installed Chrome version using multiple detection methods"""
    try:
        # Try multiple commands to detect Chrome version
        commands = [
            ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'],
            ['google-chrome', '--version'],
            ['chromium', '--version'],
            ['chrome', '--version']
        ]
        
        for cmd in commands:
            try:
                import subprocess
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, _ = process.communicate()
                version_str = stdout.decode('UTF-8').lower()
                if 'chrome' in version_str:
                    # Extract version using regex
                    match = re.search(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', version_str)
                    if match:
                        version = int(match.group(1))  # Major version number
                        logger.info(f"Detected Chrome version: {version}")
                        return version
            except:
                continue
        
        # If local detection fails, try getting latest version from ChromeDriver
        try:
            response = requests.get('https://chromedriver.storage.googleapis.com/LATEST_RELEASE')
            version = int(response.text.split('.')[0])
            logger.info(f"Using latest ChromeDriver version: {version}")
            return version
        except:
            logger.warning("Failed to get latest ChromeDriver version")
            
        return 133  # Default fallback version
    except Exception as e:
        logger.error(f"Error detecting Chrome version: {str(e)}")
        return 133

def get_random_user_agent():
    """Generate a random, recent user agent string"""
    os_list = ['Windows NT 10.0', 'Macintosh; Intel Mac OS X 10_15_7', 'X11; Linux x86_64']
    chrome_version = random.randint(130, 134)
    webkit_version = random.randint(537, 538)
    safari_version = random.randint(537, 538)
    
    os_string = random.choice(os_list)
    return f'Mozilla/5.0 ({os_string}) AppleWebKit/{webkit_version}.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/{safari_version}.36'

def setup_driver():
    """Setup and return the Chrome driver with enhanced anti-detection measures"""
    try:
        chrome_version = get_chrome_version()
        
        # Enhanced undetected-chromedriver options
        options = uc.ChromeOptions()
        
        # Anti-detection measures
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-save-password-bubble')
        options.add_argument('--disable-single-click-autofill')
        options.add_argument('--disable-translate')
        options.add_argument('--disable-zero-browsers-open-for-tests')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--no-first-run')
        
        # Random window size
        width = random.randint(1050, 1920)
        height = random.randint(800, 1080)
        options.add_argument(f'--window-size={width},{height}')
        
        # Random user agent
        options.add_argument(f'user-agent={get_random_user_agent()}')
        
        # Try multiple approaches to initialize the driver
        driver = None
        exceptions = []

        # Approach 1: Try undetected-chromedriver with version
        try:
            driver = uc.Chrome(
                options=options,
                version_main=chrome_version,
                use_subprocess=True,
                suppress_welcome=True
            )
            logger.info("Successfully initialized undetected-chromedriver with version")
            return driver
        except Exception as e:
            exceptions.append(f"Version-specific undetected-chromedriver failed: {str(e)}")

        # Approach 2: Try undetected-chromedriver without version
        if not driver:
            try:
                driver = uc.Chrome(
                    options=options,
                    use_subprocess=True,
                    suppress_welcome=True
                )
                logger.info("Successfully initialized undetected-chromedriver without version")
                return driver
            except Exception as e:
                exceptions.append(f"Generic undetected-chromedriver failed: {str(e)}")

        # Approach 3: Try selenium with ChromeDriverManager
        if not driver:
            try:
                chrome_options = webdriver.ChromeOptions()
                for arg in options.arguments:
                    chrome_options.add_argument(arg)
                
                # Additional selenium-specific options
                chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
                
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # Execute CDP commands to make selenium more stealthy
                driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": get_random_user_agent()})
                driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5]
                        });
                        window.chrome = {
                            runtime: {}
                        };
                    '''
                })
                
                logger.info("Successfully initialized selenium WebDriver")
                return driver
            except Exception as e:
                exceptions.append(f"Selenium WebDriver failed: {str(e)}")

        # If all approaches failed, raise an exception with details
        raise Exception("All driver initialization attempts failed:\n" + "\n".join(exceptions))

    except Exception as e:
        logger.error(f"Error in setup_driver: {str(e)}")
        raise

def wait_for_response(driver, timeout=60):
    """Wait for and extract the response from ChatGPT with enhanced error handling"""
    try:
        wait = WebDriverWait(driver, timeout)
        
        # Wait for loading indicators to disappear
        try:
            wait.until_not(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'animate-pulse')]"))
            )
        except:
            pass
        
        # Wait for the response to complete
        try:
            wait.until(
                EC.presence_of_element_located((By.XPATH, "//button[@data-testid='copy-turn-action-button']"))
            )
        except:
            pass
        
        # Multiple selectors for response extraction
        response_selectors = [
            "//div[contains(@class, 'markdown prose')]//p",
            "//div[@data-message-author-role='assistant']//div[contains(@class, 'markdown')]//p",
            "//div[contains(@class, 'prose')]//p/a",
            "//div[contains(@class, 'markdown-content')]//p",
            "//div[contains(@class, 'response')]//p"
        ]
        
        name = ""
        url = ""
        
        for selector in response_selectors:
            try:
                elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, selector)))
                if elements:
                    for elem in elements:
                        text = elem.text.strip()
                        if text:
                            if 'linkedin.com' in text.lower():
                                url = text
                            else:
                                name = text
                    if name and url:
                        break
            except:
                continue
        
        response_text = f"{name}\n{url}" if name or url else ""
        
        # If no response found, try getting any visible text
        if not response_text:
            try:
                main_content = driver.find_element(By.XPATH, "//main")
                response_text = main_content.text
            except:
                pass
        
        return response_text.strip()
        
    except Exception as e:
        logger.error(f"Error getting response: {str(e)}")
        return f"Error: {str(e)}"

def send_prompt(driver, prompt):
    """Send prompt to ChatGPT with enhanced reliability"""
    try:
        logger.info("Attempting to send prompt...")
        time.sleep(random.uniform(1, 2))  # Random delay
        
        wait = WebDriverWait(driver, 20)
        
        # Multiple selectors for textarea
        textarea_selectors = [
            "//textarea[@id='prompt-textarea']",
            "//textarea[contains(@class, 'overflow-auto')]",
            "//textarea[@placeholder='Ask anything...']",
            "//div[contains(@class, 'bg-background')]//textarea"
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
            raise Exception("Could not find textarea")
        
        # Try multiple ways to input text
        try:
            textarea.click()
        except:
            driver.execute_script("arguments[0].click();", textarea)
        
        time.sleep(random.uniform(0.5, 1))
        textarea.clear()
        
        # Type prompt with random delays
        for char in prompt:
            textarea.send_keys(char)
            time.sleep(random.uniform(0.01, 0.03))
        
        time.sleep(random.uniform(0.5, 1))
        
        # Try multiple ways to submit
        try:
            send_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='send-button']"))
            )
            if not send_button.is_enabled():
                return False
            send_button.click()
        except:
            textarea.send_keys(Keys.RETURN)
        
        logger.info("Prompt sent successfully")
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
                # Updated to match the column name 'Company Name' from top100.csv
                companies.append(row['Company Name'].strip())
    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")
        return []
    return companies

def save_results(results):
    """Save results to both CSV and JSON formats with error handling"""
    try:
        # Save to CSV
        csv_filename = 'chatgpt_results.csv'
        json_filename = 'chatgpt_results.json'
        
        # CSV handling
        file_exists = os.path.isfile(csv_filename)
        with open(csv_filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['Company', 'Prompt', 'Response', 'Timestamp'])
            if not file_exists:
                writer.writeheader()
            if results:
                writer.writerow(results[-1])
        
        # JSON handling
        try:
            if os.path.exists(json_filename):
                with open(json_filename, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            else:
                existing_data = []
        except:
            existing_data = []
        
        if results:
            existing_data.append(results[-1])
            
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Results saved to {csv_filename} and {json_filename}")
        
    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")

def main():
    driver = None
    try:
        driver = setup_driver()
        companies = read_companies()
        results = []
        
        if not companies:
            logger.error("No companies found in CSV file")
            return
        
        logger.info("Navigating to ChatGPT...")
        driver.get("https://chat.openai.com/")
        time.sleep(random.uniform(4, 6))
        
        for i, company in enumerate(companies, 1):
            logger.info(f"Processing company {i}/{len(companies)}: {company}")
            
            prompt = f"""Provide the full name of the Chief Human Resources Officer (CHRO) of {company}, based in India, as of February 23, 2025. Ensure the response pertains exclusively to {company} and no other entity or region. Respond with only the full name, nothing else. Also give the LinkedIn URL."""
            
            max_retries = 3
            for attempt in range(max_retries):
                if send_prompt(driver, prompt):
                    response = wait_for_response(driver)
                    
                    results.append({
                        'Company': company,
                        'Prompt': prompt,
                        'Response': response,
                        'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    logger.info(f"Response received: {response}")
                    save_results(results)  # Save after each successful response
                    
                    # Random delay between companies
                    time.sleep(random.uniform(2, 4))
                    break
                else:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {company}")
                    if attempt < max_retries - 1:
                        logger.info("Refreshing page and retrying...")
                        driver.refresh()
                        time.sleep(random.uniform(4, 6))
                    else:
                        logger.error(f"Failed all attempts for {company}")
                        results.append({
                            'Company': company,
                            'Prompt': prompt,
                            'Response': 'FAILED_ALL_ATTEMPTS',
                            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        save_results(results)
            
    except Exception as e:
        logger.error(f"An error occurred in main: {str(e)}")
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

if __name__ == "__main__":
    main() 