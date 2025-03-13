import os
import csv
import json
import asyncio
import logging
from typing import Dict, Any
from services.linkedin_scraper import LinkedInScraper
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class LinkedInHeadSearcher:
    def __init__(self):
        """Initialize LinkedIn scraper"""
        self.linkedin_scraper = LinkedInScraper()
        
    async def process_company(self, company_name: str, max_retries: int = 3) -> Dict[str, Any]:
        """Process a single company and get HR contact info with retry mechanism"""
        retries = 0
        while retries < max_retries:
            try:
                logger.info(f"Processing {company_name} (Attempt {retries + 1}/{max_retries})")
                
                # Scrape LinkedIn
                linkedin_results = await self.linkedin_scraper.scrape_both_sources(company_name)
                
                linkedin_profile = None
                if linkedin_results and linkedin_results.get('linkedin_results'):
                    linkedin_profile = linkedin_results['linkedin_results'][0]
                
                return {
                    "company": company_name,
                    "head_info": {
                        "name": linkedin_profile.get('name', '').replace(f" - {company_name}", "") if linkedin_profile else "Information Not Available",
                        "url": linkedin_profile.get('url', '') if linkedin_profile else "",
                        "title": linkedin_profile.get('title', '') if linkedin_profile else "",
                        "location": linkedin_profile.get('location', '') if linkedin_profile else "",
                        "snippet": linkedin_profile.get('snippet', '') if linkedin_profile else ""
                    }
                }
                    
            except Exception as e:
                retries += 1
                logger.error(f"Error processing {company_name} (Attempt {retries}/{max_retries}): {str(e)}")
                
                if retries < max_retries:
                    logger.info(f"Retrying after 5 seconds...")
                    await asyncio.sleep(5)
                    continue
                else:
                    logger.error(f"Max retries reached for {company_name}")
                    return {
                        "company": company_name,
                        "head_info": {
                            "name": "Error in Processing",
                            "url": "",
                            "title": "",
                            "location": "",
                            "snippet": str(e)
                        }
                    }

async def main():
    """Main function to process companies from top100.csv"""
    try:
        # Initialize searcher
        searcher = LinkedInHeadSearcher()
        all_results = []
        
        # Load existing results if top100.json exists
        processed_companies = set()
        if os.path.exists("top100.json"):
            try:
                with open("top100.json", 'r', encoding='utf-8') as f:
                    all_results = json.load(f)
                    processed_companies = {result["company"] for result in all_results}
                logger.info(f"Loaded {len(processed_companies)} already processed companies from top100.json")
            except json.JSONDecodeError:
                logger.warning("Error reading top100.json, starting fresh")
                all_results = []
        
        # Read companies from CSV
        try:
            with open("top100.csv", 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                companies = [row[0] for row in reader if row]
        except FileNotFoundError:
            logger.error("top100.csv not found.")
            return
        
        # Filter out already processed companies
        remaining_companies = [company for company in companies if company not in processed_companies]
        total_remaining = len(remaining_companies)
        total_companies = len(companies)
        
        logger.info(f"Found {total_remaining} companies remaining to process out of {total_companies} total companies")
        
        if total_remaining == 0:
            logger.info("All companies have already been processed!")
            return
        
        # Process remaining companies
        for i, company in enumerate(remaining_companies, 1):
            logger.info(f"Processing company {i}/{total_remaining} (Overall: {len(processed_companies) + i}/{total_companies}): {company}")
            
            result = await searcher.process_company(company)
            all_results.append(result)
            
            # Save after each company in case of interruption
            with open("top100.json", 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            
            # Add a delay between requests
            await asyncio.sleep(2)
            
        logger.info("All companies processed successfully!")
        logger.info("Results saved to top100.json")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    
    finally:
        logger.info("Processing complete!")

if __name__ == "__main__":
    asyncio.run(main()) 