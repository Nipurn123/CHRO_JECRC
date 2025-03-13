import os
import time
import asyncio
import logging
import json
import gradio as gr
from selenium import webdriver
from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import google.generativeai as genai
from crawl4ai import AsyncWebCrawler
from datetime import datetime
from automation import extract_company_data, get_formatted_company_data, get_formatted_company_markdown
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Import the LinkedIn Scraper
try:
    from services.linkedin_scraper import LinkedInScraper
except ImportError:
    logger.error("LinkedIn Scraper module not found. JECRC method will not work.")
    LinkedInScraper = None

# Function to view LinkedIn profile with debugging
def view_linkedin_profile(linkedin_url):
    # More robust URL validation and cleanup
    if not linkedin_url or linkedin_url == "Not available":
        logger.error("LinkedIn URL not available or invalid.")
        return "LinkedIn URL not available for this profile."
    
    # Log the URL before any modification for debugging
    logger.info(f"Received LinkedIn URL: '{linkedin_url}'")
    
    # Clean up the URL if needed (remove whitespace, etc.)
    linkedin_url = linkedin_url.strip()
    
    try:
        # Log the URL for debugging
        logger.info(f"Attempting to open LinkedIn URL: {linkedin_url}")
        
        command = [
            "/Users/nipurnagarwal/Desktop/Browser_Automation/100xprompt_1automation/run_browser_agent.py",
            "--llm-provider", "gemini",
            "--llm-api-key", "AIzaSyAbsQj2u_aGS_uGY6moBNT8cre9ge7VeE8",
            "--llm-model-name", "gemini-1.5-flash-latest",
            "--task", f"Open this LinkedIn profile: {linkedin_url} and review it."
        ]
        
        logger.info("Executing command: " + " ".join(command))
        
        # Use subprocess.Popen to run the command in the background
        process = subprocess.Popen(command)
        logger.info(f"Process started with PID: {process.pid}")
        
        return f"✅ Opening LinkedIn profile: {linkedin_url} (Process ID: {process.pid})"
    except Exception as e:
        logger.error(f"Error opening LinkedIn profile: {str(e)}")
        return f"❌ Error opening LinkedIn profile: {str(e)}"

# Function to execute terminal command for LinkedIn profile
def run_terminal_command_for_linkedin(linkedin_url):
    # More robust URL validation and cleanup
    if not linkedin_url or linkedin_url == "Not available":
        logger.error("LinkedIn URL not available or invalid for terminal command.")
        return "LinkedIn URL not available for terminal command."
    
    # Log the URL before any modification for debugging
    logger.info(f"Received LinkedIn URL for terminal command: '{linkedin_url}'")
    
    # Clean up the URL if needed (remove whitespace, etc.)
    linkedin_url = linkedin_url.strip()
    
    try:
        # Log the URL for debugging
        logger.info(f"Attempting to run terminal command for LinkedIn URL: {linkedin_url}")
        
        command = [
            "/Users/nipurnagarwal/Desktop/Browser_Automation/100xprompt_1automation/run_browser_agent.py",
            "--llm-provider", "gemini",
            "--llm-api-key", "AIzaSyAbsQj2u_aGS_uGY6moBNT8cre9ge7VeE8",
            "--llm-model-name", "gemini-1.5-flash-latest",
            "--task", f"Open this LinkedIn profile: {linkedin_url} and review it."
        ]
        
        command_str = " ".join(command)
        logger.info(f"Executing terminal command: {command_str}")
        
        # Use subprocess.Popen to run the command in the background
        process = subprocess.Popen(command)
        logger.info(f"Terminal command process started with PID: {process.pid}")
        
        return f"✅ Executed terminal command for LinkedIn URL: {linkedin_url} (Process ID: {process.pid})"
    except Exception as e:
        logger.error(f"Error running terminal command for LinkedIn profile: {str(e)}")
        return f"❌ Error running terminal command: {str(e)}"

# === OpenAI (ChatGPT) Implementation ===
def setup_openai_driver():
    """Setup and return the Chrome driver for OpenAI (ChatGPT) with enhanced anti-detection"""
    try:
        # First try to detect Chrome version
        try:
            import subprocess
            import re
            
            # Try multiple commands to detect Chrome version
            commands = [
                ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'],
                ['google-chrome', '--version'],
                ['chromium', '--version'],
                ['chrome', '--version']
            ]
            
            chrome_version = None
            for cmd in commands:
                try:
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, _ = process.communicate()
                    version_str = stdout.decode('UTF-8').lower()
                    if 'chrome' in version_str:
                        # Extract version number using regex
                        match = re.search(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', version_str)
                        if match:
                            chrome_version = int(match.group(1))  # Major version number
                            logger.info(f"Detected Chrome version: {chrome_version}")
                            break
                except:
                    continue
                    
            if not chrome_version:
                # Fallback to manual version check
                import requests
                response = requests.get('https://chromedriver.storage.googleapis.com/LATEST_RELEASE')
                chrome_version = int(response.text.split('.')[0])
                logger.info(f"Using latest ChromeDriver version: {chrome_version}")
                
        except Exception as e:
            logger.warning(f"Could not detect Chrome version: {str(e)}")
            chrome_version = None

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
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')
        
        # Random user agent
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
        ]
        import random
        options.add_argument(f'user-agent={random.choice(user_agents)}')
        
        # Add random window size
        width = random.randint(1050, 1920)
        height = random.randint(800, 1080)
        options.add_argument(f'--window-size={width},{height}')

        # Try multiple approaches to initialize the driver
        driver = None
        exceptions = []

        # Approach 1: Try undetected-chromedriver with version
        if chrome_version:
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
                from selenium import webdriver
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                
                chrome_options = webdriver.ChromeOptions()
                for arg in options.arguments:
                    chrome_options.add_argument(arg)
                
                # Add additional selenium-specific options
                chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
                
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # Execute CDP commands to make selenium more stealthy
                driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": random.choice(user_agents)})
                driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        })
                    '''
                })
                
                logger.info("Successfully initialized selenium WebDriver")
                return driver
            except Exception as e:
                exceptions.append(f"Selenium WebDriver failed: {str(e)}")

        # If all approaches failed, raise an exception with details
        raise Exception("All driver initialization attempts failed:\n" + "\n".join(exceptions))

    except Exception as e:
        logger.error(f"Error in setup_openai_driver: {str(e)}")
        return None

def openai_wait_for_response(driver, timeout=60):
    """Wait for and extract the response from ChatGPT"""
    try:
        wait = WebDriverWait(driver, timeout)
        
        # Wait for the response to complete
        try:
            wait.until(
                EC.presence_of_element_located((By.XPATH, "//button[@data-testid='copy-turn-action-button']"))
            )
        except:
            pass
        
        response_selectors = [
            "//div[contains(@class, 'markdown prose')]//p",
            "//div[@data-message-author-role='assistant']//div[contains(@class, 'markdown')]//p",
            "//div[contains(@class, 'prose')]//p/a",
        ]
        
        name = ""
        url = ""
        
        for selector in response_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
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
        
        return response_text.strip()
        
    except Exception as e:
        logger.error(f"Error getting OpenAI response: {str(e)}")
        return f"Error: {str(e)}"

def openai_send_prompt(driver, prompt):
    """Send prompt to ChatGPT"""
    try:
        time.sleep(1)
        
        wait = WebDriverWait(driver, 20)
        
        textarea = wait.until(
            EC.presence_of_element_located((By.ID, "prompt-textarea"))
        )
        
        textarea.clear()
        textarea.send_keys(prompt)
        time.sleep(0.5)
        
        send_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='send-button']"))
        )
        send_button.click()
        
        return True
        
    except Exception as e:
        logger.error(f"Error sending prompt to OpenAI: {str(e)}")
        return False

def search_with_openai(company_name, progress=None):
    """Search for CHRO using OpenAI (ChatGPT)"""
    if progress:
        progress(0.1, "Initializing OpenAI (ChatGPT) search...")
    
    driver = setup_openai_driver()
    if not driver:
        return "Failed to initialize OpenAI driver"
    
    try:
        if progress:
            progress(0.3, "Navigating to ChatGPT...")
        
        driver.get("https://chat.openai.com/")
        time.sleep(5)
        
        if progress:
            progress(0.5, "Sending prompt to ChatGPT...")
        
        prompt = f"""Provide the full name of the Chief Human Resources Officer (CHRO) of {company_name}, based in India, as of February 23, 2025. Ensure the response pertains exclusively to {company_name} and no other entity or region. Respond with only the full name, nothing else. Also give the LinkedIn URL."""
        
        if openai_send_prompt(driver, prompt):
            if progress:
                progress(0.7, "Waiting for ChatGPT response...")
            
            response = openai_wait_for_response(driver)
            
            if progress:
                progress(1.0, "OpenAI search complete!")
                
            return response
        else:
            return f"Failed to send prompt to ChatGPT for {company_name}"
            
    except Exception as e:
        logger.error(f"Error in OpenAI search: {str(e)}")
        return f"Error in OpenAI search: {str(e)}"
        
    finally:
        driver.quit()

# === Google (Gemini) Implementation ===
def extract_json_from_text(text):
    try:
        # Find the first { and last }
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != 0:
            json_str = text[start:end]
            return json_str
    except:
        pass
    return text

async def search_with_google_async(company_name, progress_callback=None):
    """Search for CHRO using Google (Gemini)"""
    try:
        if progress_callback:
            progress_callback(0.1, "Initializing Google (Gemini) search...")
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        if progress_callback:
            progress_callback(0.3, "Setting up web crawler...")
        
        async with AsyncWebCrawler() as crawler:
            if progress_callback:
                progress_callback(0.5, "Performing Google search...")
            
            search_query = f"who is the CHRO of {company_name} India linkedin"
            result = await crawler.arun(url=f"https://www.google.com/search?q={'+'.join(search_query.split())}")
            
            # Extract relevant section
            content = result.markdown
            start_idx = content.find("Advanced Search")
            if start_idx != -1:
                content = content[start_idx:]
            
            if progress_callback:
                progress_callback(0.7, "Processing with Gemini...")
            
            # Process with Gemini
            prompt = f"""
            Based on the following search results about {company_name}'s CHRO, provide only:
            1. CHRO of India Name
            2. LinkedIn URL (if available)
            
            Return ONLY a valid JSON object in this exact format, nothing else:
            {{
                "company": "{company_name}",
                "chro_name": "name",
                "linkedin_url": "url or null"
            }}
            
            Search results:
            {content}
            """
            
            response = model.generate_content(prompt)
            result_text = extract_json_from_text(response.text)
            
            if progress_callback:
                progress_callback(1.0, "Google search complete!")
                
            return result_text
            
    except Exception as e:
        logger.error(f"Error in Google search: {str(e)}")
        return f"Error in Google search: {str(e)}"

def search_with_google(company_name, progress=None):
    """Wrapper for async Google search function"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(search_with_google_async(company_name, progress))
    loop.close()
    return result

# === JECRC (LinkedIn) Implementation ===
async def search_with_jecrc_async(company_name, progress_callback=None):
    """Search for CHRO using JECRC (LinkedIn)"""
    if not LinkedInScraper:
        return "LinkedIn Scraper module not available"
    
    try:
        if progress_callback:
            progress_callback(0.1, "Initializing JECRC (LinkedIn) search...")
        
        linkedin_scraper = LinkedInScraper()
        
        if progress_callback:
            progress_callback(0.4, f"Searching LinkedIn for {company_name} CHRO...")
        
        # Scrape LinkedIn
        linkedin_results = await linkedin_scraper.scrape_both_sources(company_name)
        
        if progress_callback:
            progress_callback(0.8, "Processing LinkedIn results...")
        
        if linkedin_results and linkedin_results.get('linkedin_results'):
            linkedin_profile = linkedin_results['linkedin_results'][0]
            
            result = {
                "company": company_name,
                "head_info": {
                    "name": linkedin_profile.get('name', '').replace(f" - {company_name}", "") if linkedin_profile else "Information Not Available",
                    "url": linkedin_profile.get('url', '') if linkedin_profile else "",
                    "title": linkedin_profile.get('title', '') if linkedin_profile else "",
                    "location": linkedin_profile.get('location', '') if linkedin_profile else "",
                    "snippet": linkedin_profile.get('snippet', '') if linkedin_profile else ""
                }
            }
            
            if progress_callback:
                progress_callback(1.0, "JECRC search complete!")
                
            return f"Name: {result['head_info']['name']}\nTitle: {result['head_info']['title']}\nURL: {result['head_info']['url']}\nLocation: {result['head_info']['location']}"
        else:
            return f"No LinkedIn results found for {company_name}"
            
    except Exception as e:
        logger.error(f"Error in JECRC search: {str(e)}")
        return f"Error in JECRC search: {str(e)}"

def search_with_jecrc(company_name, progress=None):
    """Wrapper for async JECRC search function"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(search_with_jecrc_async(company_name, progress))
    loop.close()
    return result

# === Perplexity Implementation ===
def setup_perplexity_driver():
    """Setup and return the Chrome driver for Perplexity"""
    options = uc.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument("--window-size=1920,1080")
    
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
    options.add_argument(f'user-agent={user_agent}')
    
    try:
        # Try to detect Chrome version
        try:
            import subprocess
            process = subprocess.Popen(
                ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'],
                stdout=subprocess.PIPE
            )
            version = process.communicate()[0].decode('UTF-8').replace('Google Chrome ', '').strip()
            chrome_version = int(version.split('.')[0])
        except:
            chrome_version = 133  # Default to latest version if can't detect
            
        driver = uc.Chrome(
            options=options,
            version_main=chrome_version
        )
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        logger.error(f"Error initializing Perplexity driver with version: {str(e)}")
        try:
            return uc.Chrome(options=options)
        except Exception as fallback_error:
            logger.error(f"Perplexity driver fallback also failed: {str(fallback_error)}")
            return None

def perplexity_wait_for_response(driver, timeout=60):
    """Wait for and extract the response from Perplexity"""
    try:
        wait = WebDriverWait(driver, timeout)
        
        # Wait for the loading indicator to disappear
        try:
            wait_loading = WebDriverWait(driver, 30)
            wait_loading.until_not(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'animate-pulse')]"))
            )
        except Exception as e:
            logger.warning(f"Loading indicator not found or didn't disappear: {str(e)}")
        
        # Try different selectors for the response
        response_selectors = [
            "//div[contains(@class, 'prose')]//p",
            "//div[contains(@class, 'markdown-content')]//p",
            "//div[contains(@class, 'response')]//p",
            "//div[contains(@class, 'answer-content')]//p"
        ]
        
        response_text = ""
        for selector in response_selectors:
            try:
                wait_response = WebDriverWait(driver, 15)
                elements = wait_response.until(
                    EC.presence_of_all_elements_located((By.XPATH, selector))
                )
                response_text = "\n".join([elem.text for elem in elements if elem.text.strip()])
                if response_text:
                    break
            except:
                continue
        
        # If no text found, try a more general approach
        if not response_text:
            try:
                main_content = driver.find_element(By.XPATH, "//main")
                response_text = main_content.text
            except:
                pass
        
        # If still no response, take a screenshot if possible
        if not response_text:
            try:
                screenshot_path = f"perplexity_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                driver.save_screenshot(screenshot_path)
                logger.warning(f"No response found. Screenshot saved to {screenshot_path}")
            except:
                pass
            
            return "Failed to extract response from Perplexity"
        
        return response_text.strip()
        
    except Exception as e:
        logger.error(f"Error getting Perplexity response: {str(e)}")
        return f"Error: {str(e)}"

def perplexity_send_prompt(driver, prompt):
    """Send prompt to Perplexity"""
    try:
        time.sleep(2)
        
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
        return True
        
    except Exception as e:
        logger.error(f"Error sending prompt to Perplexity: {str(e)}")
        return False

def search_with_perplexity(company_name, progress=None):
    """Search for CHRO using Perplexity"""
    if progress:
        progress(0.1, "Initializing Perplexity search...")
    
    driver = setup_perplexity_driver()
    if not driver:
        return "Failed to initialize Perplexity driver"
    
    try:
        if progress:
            progress(0.3, "Navigating to Perplexity...")
        
        driver.get("https://www.perplexity.ai/")
        time.sleep(5)
        
        if progress:
            progress(0.5, "Sending prompt to Perplexity...")
        
        prompt = f"""Provide the full name of the Chief Human Resources Officer (CHRO) of {company_name}, based in India, as of February 23, 2025. Ensure the response pertains exclusively to {company_name} and no other entity or region. Respond with only the full name, nothing else. Also give the LinkedIn URL."""
        
        if perplexity_send_prompt(driver, prompt):
            if progress:
                progress(0.7, "Waiting for Perplexity response...")
            
            response = perplexity_wait_for_response(driver)
            
            if progress:
                progress(1.0, "Perplexity search complete!")
                
            return response
        else:
            return f"Failed to send prompt to Perplexity for {company_name}"
            
    except Exception as e:
        logger.error(f"Error in Perplexity search: {str(e)}")
        return f"Error in Perplexity search: {str(e)}"
        
    finally:
        driver.quit()

# === New Functions for Storage and Summary ===
def store_results(company_name, perplexity_result, openai_result, google_result, linkedin_head_result):
    """Store the results in a JSON file"""
    try:
        data = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'company': company_name,
            'perplexity_result': {
                'Response': perplexity_result,
                'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            'openai_result': {
                'Response': openai_result,
                'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            'google_result': {
                'chro_name': google_result.split("\n")[0] if "\n" in google_result else google_result,
                'linkedin_url': google_result.split("\n")[1] if "\n" in google_result and len(google_result.split("\n")) > 1 else "Not found"
            },
            'linkedin_head_result': {
                'head_info': {
                    'name': linkedin_head_result.split("Name: ")[1].split("\n")[0] if "Name: " in linkedin_head_result else "Information Not Available",
                    'title': linkedin_head_result.split("Title: ")[1].split("\n")[0] if "Title: " in linkedin_head_result else "",
                    'url': linkedin_head_result.split("URL: ")[1].split("\n")[0] if "URL: " in linkedin_head_result else "",
                    'location': linkedin_head_result.split("Location: ")[1].split("\n")[0] if "Location: " in linkedin_head_result else ""
                }
            }
        }
        
        filename = 'chro_results.json'
        # Read existing data if file exists
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                try:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]
                except:
                    existing_data = []
        else:
            existing_data = []
            
        # Add new data
        existing_data.append(data)
        
        # Write back to file
        with open(filename, 'w') as f:
            json.dump(existing_data, f, indent=4)
            
        return True
    except Exception as e:
        logger.error(f"Error storing results: {str(e)}")
        return False

def format_data_for_prompt(company_name, perplexity_result, openai_result, google_result, linkedin_result):
    """Format the data in a clear way for summary generation"""
    # Format Google result
    google_name = google_result.split("\n")[0] if "\n" in google_result else google_result
    google_linkedin = google_result.split("\n")[1] if "\n" in google_result and len(google_result.split("\n")) > 1 else "No URL available"
    google_info = f"{google_name} - LinkedIn: {google_linkedin}" if google_linkedin else google_name
    
    # Format LinkedIn result
    linkedin_parts = linkedin_result.split("\n")
    linkedin_head_str = linkedin_result
    
    # Format the data
    formatted_data = f"""
Source 1 (Perplexity AI): {perplexity_result}

Source 2 (OpenAI): {openai_result}

Source 3 (Google Search): {google_info}

Source 4 (LinkedIn Head Search): {linkedin_head_str}
"""
    return formatted_data

def get_final_summary(company_name, perplexity_result, openai_result, google_result, linkedin_result, progress=None):
    """Generate a final summary using Gemini 1.5 Flash"""
    try:
        # Store results first
        store_results(company_name, perplexity_result, openai_result, google_result, linkedin_result)
        
        # Format data for the prompt
        formatted_data = format_data_for_prompt(company_name, perplexity_result, openai_result, google_result, linkedin_result)
        
        if progress:
            progress(0.1, "Initializing Gemini 1.5 Flash for final summary...")
        
        try:
            # Use Gemini 1.5 Flash model
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            if progress:
                progress(0.5, "Sending summary request to Gemini...")
            
            summary_prompt = f"""Act as a professional HR data analyst. I have gathered information about the CHRO (Chief Human Resources Officer) of {company_name} from four different sources. Here is the verified data:

{formatted_data}

Based on these sources, I need you to provide ONLY:
1. The full name of the current CHRO
2. Their LinkedIn URL

Format your response as:
Name: [Full Name]
LinkedIn: [URL]

If the information from the sources is conflicting, provide the name and URL that appears most reliable based on source consistency.
"""
            
            # Generate content with Gemini
            response = model.generate_content(summary_prompt)
            final_summary = response.text
            
            if progress:
                progress(1.0, "Summary generation complete!")
            
            # Store the final summary
            result = {
                'Company': company_name,
                'Final_Summary': final_summary,
                'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Store in a separate file
            try:
                with open('final_summaries.json', 'a') as f:
                    json.dump(result, f, indent=4)
                    f.write('\n')
            except Exception as e:
                logger.error(f"Error storing final summary: {str(e)}")
            
            return final_summary
                
        except Exception as e:
            logger.error(f"Error in summary generation: {str(e)}")
            return f"Error generating summary: {str(e)}"
            
    except Exception as e:
        logger.error(f"Error in get_final_summary: {str(e)}")
        return f"Error: {str(e)}"

# Function to load final summaries from the JSON file
def load_final_summaries():
    """Load and return all final summaries from final_summaries.json"""
    try:
        if not os.path.exists('final_summaries.json'):
            return "No final summaries found. Generate summaries first."
        
        with open('final_summaries.json', 'r') as f:
            content = f.read()
            
        # Split by newlines since each JSON object is on a separate line
        json_objects = [line.strip() for line in content.split('\n') if line.strip()]
        
        results = []
        for json_obj in json_objects:
            try:
                data = json.loads(json_obj)
                results.append(data)
            except json.JSONDecodeError:
                continue
        
        if not results:
            return "No valid summaries found in final_summaries.json"
        
        # Format the results
        formatted_output = ""
        for i, result in enumerate(results, 1):
            formatted_output += f"Summary #{i}:\n"
            formatted_output += f"Company: {result.get('Company', 'Unknown')}\n"
            formatted_output += f"Timestamp: {result.get('Timestamp', 'Unknown')}\n"
            formatted_output += f"Summary:\n{result.get('Final_Summary', 'Not available')}\n"
            formatted_output += "-" * 50 + "\n"
        
        return formatted_output
    
    except Exception as e:
        logger.error(f"Error loading final summaries: {str(e)}")
        return f"Error loading final summaries: {str(e)}"

# === Gradio Interface ===
def search_chro(company_name, progress=gr.Progress()):
    """Main function to search for CHRO using all four methods in specified order"""
    # Initialize results dictionary with status messages
    results = {
        "perplexity": "🔍 Starting Perplexity search...",
        "openai": "⏳ Waiting...",
        "google": "⏳ Waiting...",
        "jecrc": "⏳ Waiting...",
        "summary": "⏳ Waiting for all searches to complete..."
    }
    
    # First update to display initial state
    yield (
        results["perplexity"],
        results["openai"],
        results["google"],
        results["jecrc"],
        results["summary"]
    )
    
    # Add a small delay for UI to update
    time.sleep(1)
    
    # 1. Search with Perplexity (First)
    progress(0, "Starting Perplexity search...")
    results["perplexity"] = "🔍 Searching with Perplexity..."
    yield (
        results["perplexity"],
        results["openai"],
        results["google"],
        results["jecrc"],
        results["summary"]
    )
    
    # Perform the search
    perplexity_result = search_with_perplexity(company_name, lambda p, m: progress(p * 0.2, m))
    
    # Update with Perplexity result and prepare for next search
    results["perplexity"] = perplexity_result
    results["openai"] = "🔍 Starting OpenAI search..."
    progress(0.2, "Perplexity search complete!")
    
    # Add a delay to ensure UI updates and user can see the result
    time.sleep(2)
    
    # Update UI with Perplexity results
    yield (
        results["perplexity"],
        results["openai"],
        results["google"],
        results["jecrc"],
        results["summary"]
    )
    
    # Add a small delay before starting next search
    time.sleep(1)
    
    # 2. Search with OpenAI (ChatGPT) (Second)
    progress(0.2, "Starting OpenAI (ChatGPT) search...")
    results["openai"] = "🔍 Searching with OpenAI..."
    yield (
        results["perplexity"],
        results["openai"],
        results["google"],
        results["jecrc"],
        results["summary"]
    )
    
    # Perform the search
    openai_result = search_with_openai(company_name, lambda p, m: progress(0.2 + p * 0.2, m))
    
    # Update with OpenAI result and prepare for next search
    results["openai"] = openai_result
    results["google"] = "🔍 Starting Google search..."
    progress(0.4, "OpenAI search complete!")
    
    # Add a delay to ensure UI updates and user can see the result
    time.sleep(2)
    
    # Update UI with OpenAI results
    yield (
        results["perplexity"],
        results["openai"],
        results["google"],
        results["jecrc"],
        results["summary"]
    )
    
    # Add a small delay before starting next search
    time.sleep(1)
    
    # 3. Search with Google (Gemini) (Third)
    progress(0.4, "Starting Google (Gemini) search...")
    results["google"] = "🔍 Searching with Google..."
    yield (
        results["perplexity"],
        results["openai"],
        results["google"],
        results["jecrc"],
        results["summary"]
    )
    
    # Perform the search
    google_result = search_with_google(company_name, lambda p, m: progress(0.4 + p * 0.2, m))
    
    # Update with Google result and prepare for next search
    results["google"] = google_result
    results["jecrc"] = "🔍 Starting JECRC search..."
    progress(0.6, "Google search complete!")
    
    # Add a delay to ensure UI updates and user can see the result
    time.sleep(2)
    
    # Update UI with Google results
    yield (
        results["perplexity"],
        results["openai"],
        results["google"],
        results["jecrc"],
        results["summary"]
    )
    
    # Add a small delay before starting next search
    time.sleep(1)
    
    # 4. Search with JECRC (LinkedIn) (Last)
    progress(0.6, "Starting JECRC (LinkedIn) search...")
    results["jecrc"] = "🔍 Searching with JECRC..."
    yield (
        results["perplexity"],
        results["openai"],
        results["google"],
        results["jecrc"],
        results["summary"]
    )
    
    # Perform the search
    jecrc_result = search_with_jecrc(company_name, lambda p, m: progress(0.6 + p * 0.2, m))
    
    # Update with JECRC result and prepare for summary
    results["jecrc"] = jecrc_result
    results["summary"] = "🔍 Generating comprehensive summary..."
    progress(0.8, "JECRC search complete!")
    
    # Add a delay to ensure UI updates and user can see the result
    time.sleep(2)
    
    # Update UI with all search results before summary generation
    yield (
        results["perplexity"],
        results["openai"],
        results["google"],
        results["jecrc"],
        results["summary"]
    )
    
    # Add a small delay before starting summary
    time.sleep(1)
    
    # 5. Generate final summary
    progress(0.8, "Generating comprehensive summary...")
    results["summary"] = "🔍 Analyzing all results and creating summary with Gemini 1.5 Flash..."
    yield (
        results["perplexity"],
        results["openai"],
        results["google"],
        results["jecrc"],
        results["summary"]
    )
    
    # Generate the summary
    summary_result = get_final_summary(
        company_name, 
        results["perplexity"], 
        results["openai"], 
        results["google"], 
        results["jecrc"],
        lambda p, m: progress(0.8 + p * 0.2, m)
    )
    
    # Update with final summary
    results["summary"] = summary_result
    progress(1.0, "✅ Gemini 1.5 Flash summary complete!")
    
    # Add a delay to ensure UI updates with the summary
    time.sleep(1)
    
    # Final update with all results and summary
    return (
        results["perplexity"],
        results["openai"],
        results["google"],
        results["jecrc"],
        results["summary"]
    )

# Create the Gradio interface with tabs
with gr.Blocks(title="Ultimate CHRO Finder with Gemini 1.5 Flash") as demo:
    gr.Markdown("# Ultimate CHRO Finder with Gemini 1.5 Flash")
    gr.Markdown("Enter a company name to find its Chief Human Resources Officer (CHRO) using multiple search methods. A structured summary will be generated using Gemini 1.5 Flash.")
    
    with gr.Tabs():
        with gr.Tab("Search"):
            company_input = gr.Textbox(label="Company Name", placeholder="Enter company name...")
            search_button = gr.Button("Search")
            
            with gr.Row():
                perplexity_output = gr.Textbox(label="Perplexity Result", lines=5)
                openai_output = gr.Textbox(label="OpenAI (ChatGPT) Result", lines=5)
            
            with gr.Row():
                google_output = gr.Textbox(label="Google (Gemini) Result", lines=5)
                jecrc_output = gr.Textbox(label="JECRC (LinkedIn) Result", lines=5)
            
            summary_output = gr.Textbox(label="Comprehensive Summary (Gemini 1.5 Flash)", lines=5)
            
            search_button.click(
                fn=search_chro,
                inputs=company_input,
                outputs=[perplexity_output, openai_output, google_output, jecrc_output, summary_output]
            )
        
        with gr.Tab("Company Database"):
            status_box = gr.Textbox(label="Status", visible=True)
            refresh_db_button = gr.Button("Refresh Company Database")
            
            # Create a container to display all company data
            company_html = gr.HTML()
            
            # Function to update the company database display
            def update_company_database():
                data = get_formatted_company_data()
                
                if not data or not isinstance(data, list):
                    return "No company data available. Generate summaries first."
                
                # Build an HTML representation of the data with improved styling
                html_output = """
                <style>
                    .company-container {
                        max-width: 100%;
                        margin: 0 auto;
                    }
                    .company-header {
                        background-color: #2c3e50;
                        color: white;
                        padding: 15px 20px;
                        border-radius: 8px 8px 0 0;
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 20px;
                        text-align: center;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }
                    .company-card {
                        border-radius: 8px;
                        margin-bottom: 20px;
                        overflow: hidden;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                        transition: transform 0.3s ease, box-shadow 0.3s ease;
                        background-color: #ffffff;
                        border: 1px solid #e0e0e0;
                    }
                    .company-card:hover {
                        transform: translateY(-5px);
                        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
                    }
                    .company-info {
                        padding: 20px;
                        background: linear-gradient(135deg, #f8f9fa, #e9ecef);
                    }
                    .company-info p {
                        margin: 10px 0;
                        font-size: 16px;
                        line-height: 1.5;
                    }
                    .company-info strong {
                        color: #2c3e50;
                        font-weight: bold;
                    }
                    .company-action {
                        padding: 15px;
                        display: flex;
                        justify-content: space-between;
                        background-color: #f1f3f5;
                        border-top: 1px solid #e0e0e0;
                    }
                    .company-url {
                        font-weight: bold;
                        color: #3498db;
                        word-break: break-all;
                        margin-bottom: 10px;
                        display: block;
                    }
                    .view-profile-btn {
                        background-color: #4CAF50;
                        color: white;
                        padding: 10px 15px;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-weight: bold;
                        transition: background-color 0.3s ease;
                        width: 48%;
                    }
                    .terminal-cmd-btn {
                        background-color: #2196F3;
                        color: white;
                        padding: 10px 15px;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-weight: bold;
                        transition: background-color 0.3s ease;
                        width: 48%;
                    }
                    .view-profile-btn:hover {
                        background-color: #388E3C;
                    }
                    .terminal-cmd-btn:hover {
                        background-color: #0b7dda;
                    }
                    .company-link a {
                        color: #3498db;
                        text-decoration: none;
                        font-weight: bold;
                    }
                    .company-link a:hover {
                        text-decoration: underline;
                    }
                </style>
                <div class="company-container">
                    <div class="company-header">Company CHRO Database</div>
                """
                
                for i, item in enumerate(data):
                    company = item.get('company', 'Unknown')
                    name = item.get('name', 'Not available')
                    linkedin_url = item.get('linkedin_url', 'Not available')
                    timestamp = item.get('timestamp', 'Unknown')
                    
                    # Create the company card using string concatenation instead of f-strings
                    card_header = (
                        '<div class="company-card">'
                        '<div class="company-info">'
                        '<p><strong>Company:</strong> ' + company + '</p>'
                        '<p><strong>CHRO:</strong> ' + name + '</p>'
                    )
                    html_output += card_header
                    
                    # More visible and clear display of LinkedIn URL
                    if linkedin_url != "Not available":
                        # Store the LinkedIn URL directly in a data attribute for easier access
                        # Avoid f-strings for this part too
                        url_html = (
                            '<p class="company-link"><strong>LinkedIn:</strong> '
                            '<a href="' + linkedin_url + '" target="_blank" id="linkedin-display-' + str(i) + '" '
                            'data-url="' + linkedin_url + '">' + linkedin_url + '</a>'
                            '</p>'
                        )
                        html_output += url_html
                    else:
                        html_output += '<p><strong>LinkedIn:</strong> Not available</p>'
                        
                    # Add timestamp using regular string concatenation
                    timestamp_html = '<p><strong>Timestamp:</strong> ' + timestamp + '</p></div>'
                    html_output += timestamp_html
                    
                    if linkedin_url != "Not available":
                        # Avoid f-strings entirely for JavaScript portions
                        # Use regular string concatenation for the HTML with JavaScript
                        js_safe_url = linkedin_url.replace("'", "\\'")
                        
                        btn_html = (
                            '<div class="company-action">'
                            '<button class="view-profile-btn" '
                            'onclick="'
                            'var linkedinUrl = \'' + js_safe_url + '\';'
                            'console.log(\'Setting LinkedIn URL:\', linkedinUrl);'
                            'document.getElementById(\'linkedin-url-' + str(i) + '\').value = linkedinUrl;'
                            'document.getElementById(\'view-profile-' + str(i) + '\').click();">'
                            'View in Browser'
                            '</button>'
                            '<button class="terminal-cmd-btn" '
                            'onclick="'
                            'var linkedinUrl = \'' + js_safe_url + '\';'
                            'console.log(\'Setting Terminal LinkedIn URL:\', linkedinUrl);'
                            'document.getElementById(\'linkedin-url-terminal-' + str(i) + '\').value = linkedinUrl;'
                            'document.getElementById(\'run-terminal-' + str(i) + '\').click();">'
                            'Run Terminal Command'
                            '</button>'
                            '</div>'
                        )
                        
                        html_output += btn_html
                    
                    html_output += """
                    </div>
                    """
                
                html_output += """
                <script>
                    // Debug function to check if LinkedIn URLs are correctly stored
                    function debugLinkedInUrls() {
                        var links = document.querySelectorAll('[id^="linkedin-display-"]');
                        for (var i = 0; i < links.length; i++) {
                            console.log('LinkedIn URL ' + i + ':', links[i].getAttribute('data-url'));
                        }
                    }
                    
                    // Execute this on page load
                    setTimeout(debugLinkedInUrls, 1000);
                </script>
                </div>
                """
                
                return html_output
            
            # Initial load of company database
            company_html.value = update_company_database()
            
            # Add a series of invisible buttons for each possible company (up to a reasonable limit)
            # These will be triggered by the HTML buttons
            hidden_buttons = []
            hidden_urls = []
            max_companies = 20  # Set a reasonable maximum
            
            for i in range(max_companies):
                # Create a visible textbox for debugging if needed
                url_input = gr.Textbox(visible=False, elem_id=f"linkedin-url-{i}", label=f"LinkedIn URL {i}")
                hidden_urls.append(url_input)
                
                # Create the button that will be triggered by the HTML button for viewing in browser
                btn = gr.Button(f"Hidden Button {i}", visible=False, elem_id=f"view-profile-{i}")
                btn.click(fn=view_linkedin_profile, inputs=[url_input], outputs=status_box)
                hidden_buttons.append(btn)
                
                # Create additional textbox and button for terminal command
                url_input_terminal = gr.Textbox(visible=False, elem_id=f"linkedin-url-terminal-{i}", label=f"LinkedIn URL Terminal {i}")
                hidden_urls.append(url_input_terminal)
                
                # Create the button that will be triggered by the HTML button for running terminal command
                terminal_btn = gr.Button(f"Hidden Terminal Button {i}", visible=False, elem_id=f"run-terminal-{i}")
                terminal_btn.click(fn=run_terminal_command_for_linkedin, inputs=[url_input_terminal], outputs=status_box)
                hidden_buttons.append(terminal_btn)
            
            # Update when refresh button is clicked
            refresh_db_button.click(
                fn=update_company_database,
                inputs=[],
                outputs=company_html
            )

if __name__ == "__main__":
    demo.launch(share=True) 