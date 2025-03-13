import asyncio
import csv
import json
from crawl4ai import *
import google.generativeai as genai
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

def save_result(data, filename='chro_results.json'):
    try:
        # Read existing results
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                results = json.load(f)
        else:
            results = []
        
        # Append new result
        results.append(data)
        
        # Save updated results
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
    except Exception as e:
        print(f"Error saving result: {str(e)}")

def extract_json_from_text(text):
    try:
        # Find the first { and last }
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != 0:
            json_str = text[start:end]
            return json.loads(json_str)
    except:
        pass
    return None

async def process_company(company, crawler, max_retries=3):
    for attempt in range(max_retries):
        try:
            search_query = f"who is the CHRO of {company} India linkedin"
            result = await crawler.arun(url=f"https://www.google.com/search?q={'+'.join(search_query.split())}")
            
            # Extract relevant section (from Advanced Search till end)
            content = result.markdown
            start_idx = content.find("Advanced Search")
            if start_idx != -1:
                content = content[start_idx:]
            
            # Process with Gemini
            prompt = f"""
            Based on the following search results about {company}'s CHRO, provide only:
            1. CHRO  of India Name
            2. LinkedIn URL (if available)
            
            Return ONLY a valid JSON object in this exact format, nothing else:
            {{
                "company": "{company}",
                "chro_name": "name",
                "linkedin_url": "url or null"
            }}
            
            Search results:
            {content}
            """
            
            response = model.generate_content(prompt)
            result_json = extract_json_from_text(response.text)
            
            if result_json:
                # Save result immediately
                save_result(result_json)
                print(f"Successfully saved data for {company}")
            else:
                # If JSON parsing failed, create error result
                result_json = {
                    "company": company,
                    "chro_name": "ERROR",
                    "linkedin_url": "Failed to parse Gemini response"
                }
                save_result(result_json)
                print(f"Failed to parse response for {company}")
            
            return result_json
            
        except Exception as e:
            if "429" in str(e) or "exhausted" in str(e).lower():
                if attempt < max_retries - 1:  # Don't sleep on last attempt
                    print(f"Rate limit hit for {company}, sleeping for 10 seconds...")
                    await asyncio.sleep(10)
                    continue
            print(f"Error processing {company}: {str(e)}")
            # Save error result
            error_result = {
                "company": company,
                "chro_name": "ERROR",
                "linkedin_url": str(e)
            }
            save_result(error_result)
            return error_result

async def main():
    # Read companies from CSV
    companies = []
    with open('top100.csv', 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if row and row[0].strip():  # Skip empty rows
                companies.append(row[0].strip())
    
    # Create fresh results file
    if os.path.exists('chro_results.json'):
        os.remove('chro_results.json')
    
    async with AsyncWebCrawler() as crawler:
        for company in companies:
            result = await process_company(company, crawler)
            print(f"Processed {company}")
            # Add small delay between requests to avoid rate limiting
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
