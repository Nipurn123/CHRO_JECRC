import asyncio
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import platform
from selenium.webdriver.common.keys import Keys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LinkedInScraper:
    def __init__(self):
        self.setup_chrome_options()

    def setup_chrome_options(self):
        """Setup Chrome options for scraping"""
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless=new')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument('--disable-notifications')
        self.chrome_options.add_argument('--disable-extensions')
        self.chrome_options.add_argument('--disable-infobars')
        self.chrome_options.add_argument('--disable-popup-blocking')
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    def get_webdriver(self):
        """Get appropriate WebDriver based on platform"""
        try:
            if platform.system() == 'Darwin' and platform.machine() == 'arm64':
                # Special handling for Mac M1/M2
                service = Service()
                driver = webdriver.Chrome(service=service, options=self.chrome_options)
            else:
                # For other platforms
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=self.chrome_options)
            
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            logger.error(f"Error creating WebDriver: {str(e)}")
            raise

    async def scrape_both_sources(self, company_name):
        """Scrape LinkedIn profiles and return the first valid result"""
        try:
            # Get LinkedIn results
            logger.info("Scraping LinkedIn via RecruitmentGeek...")
            linkedin_results = await self.extract_profiles(
                search_query="HR Head",
                company_name=company_name,
                location="India",
                max_results=5
            )
            logger.info(f"LinkedIn scraping completed. Found {len(linkedin_results)} results.")
            
            # Get the first valid profile
            first_profile = linkedin_results[0] if linkedin_results else None
            if first_profile:
                logger.info(f"Selected profile: {json.dumps(first_profile, indent=2)}")
            else:
                logger.warning("No valid profiles found")
            
            return {
                "linkedin_results": linkedin_results,
                "selected_profile": first_profile
            }
            
        except Exception as e:
            logger.error(f"Error in LinkedIn scraping: {str(e)}")
            return {
                "linkedin_results": [],
                "selected_profile": None
            }

    async def scrape_ai_sources(self, company_name):
        """Get results from ChatGPT and Perplexity"""
        driver = None
        try:
            driver = self.get_webdriver()
            wait = WebDriverWait(driver, 20)
            ai_results = []
            
            # Step 1: ChatGPT
            try:
                logger.info("Accessing ChatGPT...")
                driver.get("https://chat.openai.com")
                time.sleep(5)
                
                query = f"Find the Head of HR or HR Director at {company_name} India. Include their full name, current position, and LinkedIn URL if available. Format the response as a list."
                
                input_box = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[placeholder='Message ChatGPT…']"))
                )
                input_box.send_keys(query)
                input_box.send_keys(Keys.RETURN)
                
                time.sleep(10)
                response_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".markdown-content p"))
                )
                chatgpt_response = response_element.text
                logger.info(f"ChatGPT Response: {chatgpt_response}")
                
                ai_results.append({
                    "source": "chatgpt",
                    "response": chatgpt_response
                })
                
            except Exception as e:
                logger.error(f"Error in ChatGPT scraping: {str(e)}")
            
            # Step 2: Perplexity
            try:
                logger.info("Accessing Perplexity...")
                driver.get("https://www.perplexity.ai")
                time.sleep(5)
                
                query = f"Who is the Head of HR or HR Director at {company_name} India? Include their LinkedIn profile if possible."
                
                input_box = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[placeholder='Ask anything...']"))
                )
                input_box.send_keys(query)
                input_box.send_keys(Keys.RETURN)
                
                time.sleep(10)
                response_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".response-content"))
                )
                perplexity_response = response_element.text
                logger.info(f"Perplexity Response: {perplexity_response}")
                
                ai_results.append({
                    "source": "perplexity",
                    "response": perplexity_response
                })
                
            except Exception as e:
                logger.error(f"Error in Perplexity scraping: {str(e)}")
            
            return ai_results
            
        except Exception as e:
            logger.error(f"Error in AI sources scraping: {str(e)}")
            return []
        finally:
            if driver:
                driver.quit()

    async def extract_profiles(self, search_query="HR", company_name="", location="", max_results=5):
        """Extract LinkedIn profiles using async execution"""
        logger.info(f"Starting profile extraction for {company_name} in {location}")
        
        try:
            loop = asyncio.get_event_loop()
            profiles = await loop.run_in_executor(
                None, self._extract_profiles_sync, search_query, company_name, location, max_results
            )
            return profiles[:max_results]
        except Exception as e:
            logger.error(f"Error in extract_profiles: {str(e)}")
            raise

    def _extract_profiles_sync(self, search_query, company_name, location, max_results):
        """Synchronous part of profile extraction"""
        driver = None
        try:
            driver = self.get_webdriver()
            all_profiles = []
            full_search_query = f"{search_query} {company_name} {location}".strip()
            
            base_url = "https://recruitmentgeek.com/tools/linkedin"
            driver.get(base_url)
            
            wait = WebDriverWait(driver, 20)
            
            # Retry loop for search box
            max_retries = 3
            retries = 0
            while retries < max_retries:
                try:
                    search_box = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input.gsc-input"))
                    )
                    search_box.clear()
                    search_box.send_keys(full_search_query)
                    
                    search_button = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.gsc-search-button"))
                    )
                    
                    driver.execute_script("arguments[0].scrollIntoView(true);", search_button)
                    time.sleep(1)
                    
                    try:
                        search_button.click()
                    except:
                        driver.execute_script("arguments[0].click();", search_button)
                    
                    time.sleep(5)
                    break
                    
                except Exception as e:
                    retries += 1
                    logger.error(f"Error in search attempt {retries}/{max_retries}: {str(e)}")
                    if retries < max_retries:
                        logger.info(f"Retrying after 5 seconds...")
                        time.sleep(5)
                        continue
                    else:
                        logger.error("Max retries reached for search operation")
                        raise
            
            results = driver.find_elements(By.CSS_SELECTOR, ".gsc-webResult")
            
            for result in results[:max_results]:
                try:
                    profile = self._extract_profile_data(result)
                    if profile:
                        all_profiles.append(profile)
                except Exception as e:
                    logger.error(f"Error extracting profile data: {str(e)}")
                    continue
            
            return all_profiles
            
        except Exception as e:
            logger.error(f"Error in _extract_profiles_sync: {str(e)}")
            raise
        finally:
            if driver:
                driver.quit()

    def _extract_profile_data(self, result):
        """Extract data from a single search result"""
        try:
            title_elem = result.find_element(By.CSS_SELECTOR, ".gs-title a:first-child")
            title = title_elem.text
            url = title_elem.get_attribute("href")
            
            if 'linkedin.com/in/' not in url:
                return None
                
            url = re.sub(r'\?.*$', '', url)
            name = title.replace(' | Professional Profile', '')
            name = re.sub(r'\s+\|\s+LinkedIn.*$', '', name)
            
            snippet = result.find_element(By.CSS_SELECTOR, ".gs-snippet").text
            
            company = ''
            location = ''
            
            if snippet:
                company_match = re.search(r'at\s+([^|.]+)', snippet)
                location_match = re.search(r'in\s+([^|.]+)', snippet)
                
                if company_match:
                    company = company_match.group(1).strip()
                if location_match:
                    location = location_match.group(1).strip()
            
            return {
                'name': name,
                'url': url,
                'company': company,
                'location': location,
                'snippet': snippet
            }
            
        except Exception as e:
            logger.error(f"Error extracting profile data: {str(e)}")
            return None

    async def search_hr_contacts(self, company_name, location=""):
        """Search for HR contacts at a specific company"""
        try:
            logger.info(f"Searching HR contacts for {company_name} in {location}")
            profiles = await self.extract_profiles(
                search_query="HR",
                company_name=company_name,
                location=location,
                max_results=5
            )
            return profiles
        except Exception as e:
            logger.error(f"Error searching HR contacts: {str(e)}")
            raise 