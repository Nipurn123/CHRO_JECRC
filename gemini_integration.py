import os
import asyncio
import json
from datetime import datetime
import logging
from dotenv import load_dotenv
from services.gemini_direct_search import GeminiDirectSearcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get API key from environment variables
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

# Initialize the GeminiDirectSearcher
gemini_searcher = GeminiDirectSearcher(api_key=GEMINI_API_KEY)

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

async def get_final_summary_with_gemini_direct(company_name, perplexity_result, openai_result, google_result, linkedin_result, progress=None):
    """Generate a final summary using GeminiDirectSearcher"""
    try:
        # Store results first
        store_results(company_name, perplexity_result, openai_result, google_result, linkedin_result)
        
        if progress:
            progress(0.1, "Initializing Gemini for final summary...")
        
        try:
            # Generate summary using GeminiDirectSearcher
            if progress:
                progress(0.5, "Sending summary request to Gemini Direct Searcher...")
            
            summary_result = await gemini_searcher.generate_summary(
                company_name=company_name,
                perplexity_result=perplexity_result,
                openai_result=openai_result,
                google_result=google_result,
                linkedin_result=linkedin_result,
                model_id="gemini-1.5-flash"  # You can use other models as needed
            )
            
            if summary_result.get('error'):
                logger.error(f"Error in summary generation: {summary_result['error']}")
                return f"Error generating summary: {summary_result['error']}"
                
            final_summary = summary_result.get('summary', '')
            
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
        logger.error(f"Error in get_final_summary_with_gemini_direct: {str(e)}")
        return f"Error: {str(e)}"

# Example usage function
async def example_usage():
    """Example of how to use the get_final_summary_with_gemini_direct function"""
    # Example data from all 4 sources
    company_name = "Tata Consultancy Services"
    
    perplexity_result = "The CHRO of Tata Consultancy Services (TCS) India is Milind Lakkad. He was appointed as the CHRO in 2019 and oversees global HR functions."
    
    openai_result = "Milind Lakkad\nhttps://www.linkedin.com/in/milind-lakkad-b4567/"
    
    google_result = "Milind Lakkad - LinkedIn: https://www.linkedin.com/in/milind-lakkad-89012/"
    
    linkedin_result = "Name: Milind Lakkad\nTitle: Chief Human Resources Officer\nURL: https://www.linkedin.com/in/milind-lakkad-34567/\nLocation: Mumbai, India"
    
    # Simple progress callback for example purposes
    def progress_callback(value, message):
        print(f"Progress: {value*100:.0f}% - {message}")
    
    # Generate summary
    print(f"Generating summary for {company_name}...")
    summary = await get_final_summary_with_gemini_direct(
        company_name, 
        perplexity_result, 
        openai_result, 
        google_result, 
        linkedin_result,
        progress=progress_callback
    )
    
    print("\n=== Final Summary ===\n")
    print(summary)

# Run the example if this script is executed directly
if __name__ == "__main__":
    asyncio.run(example_usage()) 