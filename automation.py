import json
import os
import re
import sys
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_linkedin_url(text):
    """Extract LinkedIn URL from text using regex"""
    if not text or not isinstance(text, str):
        return "Not available"
        
    linkedin_pattern = r'https?://(?:www\.|in\.)?linkedin\.com/in/[a-zA-Z0-9_-]+'
    match = re.search(linkedin_pattern, text)
    return match.group(0) if match else "Not available"

def extract_company_data():
    """Extract company names and LinkedIn URLs from final_summaries.json"""
    try:
        # Get the absolute path of the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, 'final_summaries.json')
        
        # Check for file existence
        if not os.path.exists(file_path):
            # Try current working directory as fallback
            cwd_path = os.path.join(os.getcwd(), 'final_summaries.json')
            if os.path.exists(cwd_path):
                file_path = cwd_path
                logger.info(f"Using file at current working directory: {file_path}")
            else:
                logger.warning(f"final_summaries.json not found at {file_path} or {cwd_path}")
                return []

        logger.info(f"Reading file from: {file_path}")
        
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            logger.warning("final_summaries.json is empty")
            return []
            
        logger.info(f"File content length: {len(content)} characters")
        
        # Fix for malformed JSON - find all JSON objects
        results = []
        
        # First try to parse as a JSON array
        try:
            # Check if the content starts with [ and ends with ]
            if content.strip().startswith('[') and content.strip().endswith(']'):
                data_array = json.loads(content)
                logger.info(f"Successfully parsed content as JSON array with {len(data_array)} items")
                
                for data in data_array:
                    try:
                        company_name = data.get('Company', 'Unknown')
                        final_summary = data.get('Final_Summary', '')
                        
                        # Extract LinkedIn URL
                        linkedin_url = extract_linkedin_url(final_summary)
                        
                        # Extract name using regex
                        name_match = re.search(r'Name:\s*([^\n]+)', final_summary)
                        name = name_match.group(1).strip() if name_match else "Not available"
                        
                        # Create result object
                        result = {
                            'company': company_name,
                            'name': name,
                            'linkedin_url': linkedin_url,
                            'timestamp': data.get('Timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        }
                        
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Error processing array item: {str(e)}")
                        continue
                
                # If we successfully parsed data, return it
                if results:
                    logger.info(f"Extracted {len(results)} companies from JSON array")
                    return results
        except json.JSONDecodeError:
            logger.info("Content is not a valid JSON array, trying individual JSON objects")
        except Exception as e:
            logger.error(f"Error parsing JSON array: {str(e)}")
        
        # If array parsing failed, try finding individual JSON objects
        logger.info("Attempting to extract individual JSON objects")
        
        # More robust pattern to match JSON objects - looks for content between { and }
        # This handles nested braces more effectively
        pattern = r'\{(?:[^{}]|(?R))*\}'
        
        # Fallback to simpler pattern if re.DOTALL is not supported or for compatibility
        try:
            json_matches = re.findall(pattern, content, re.DOTALL)
        except Exception:
            # Fallback to simpler but less accurate pattern
            pattern = r'\{[^{]*?\}'
            json_matches = re.findall(pattern, content, re.DOTALL)
        
        logger.info(f"Found {len(json_matches)} potential JSON objects")
        
        for json_str in json_matches:
            try:
                data = json.loads(json_str)
                company_name = data.get('Company', 'Unknown')
                final_summary = data.get('Final_Summary', '')
                
                if not company_name or company_name == 'Unknown':
                    continue
                
                # Extract LinkedIn URL
                linkedin_url = extract_linkedin_url(final_summary)
                
                # Extract name using regex
                name_match = re.search(r'Name:\s*([^\n]+)', final_summary)
                name = name_match.group(1).strip() if name_match else "Not available"
                
                # Create result object
                result = {
                    'company': company_name,
                    'name': name,
                    'linkedin_url': linkedin_url,
                    'timestamp': data.get('Timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                }
                
                results.append(result)
                logger.info(f"Successfully extracted data for company: {company_name}")
            except json.JSONDecodeError:
                logger.warning(f"Error decoding JSON object: {json_str[:50]}...")
                continue
            except Exception as e:
                logger.error(f"Error processing object: {str(e)}")
                continue
        
        # If no results found, try one last method - line by line parsing
        if not results:
            logger.info("Trying line-by-line parsing as a last resort")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('{') and line.endswith('}'):
                            try:
                                data = json.loads(line)
                                company_name = data.get('Company', 'Unknown')
                                final_summary = data.get('Final_Summary', '')
                                
                                # Extract LinkedIn URL
                                linkedin_url = extract_linkedin_url(final_summary)
                                
                                # Extract name using regex
                                name_match = re.search(r'Name:\s*([^\n]+)', final_summary)
                                name = name_match.group(1).strip() if name_match else "Not available"
                                
                                # Create result object
                                result = {
                                    'company': company_name,
                                    'name': name,
                                    'linkedin_url': linkedin_url,
                                    'timestamp': data.get('Timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                                }
                                
                                results.append(result)
                            except:
                                continue
            except Exception as e:
                logger.error(f"Error in line-by-line parsing: {str(e)}")
        
        logger.info(f"Final extraction result: {len(results)} companies")
        return results
    except Exception as e:
        logger.error(f"Error extracting company data: {str(e)}")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logger.error(f"Exception details: {exc_type}, {fname}, line {exc_tb.tb_lineno}")
        return []

def save_extracted_data(data, filename='extracted_company_data.json'):
    """Save extracted data to a JSON file"""
    try:
        # Get the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"Successfully saved data to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving extracted data: {str(e)}")
        return False

def get_formatted_company_data():
    """Get extracted company data in a formatted string"""
    data = extract_company_data()
    
    if not data:
        logger.warning("No company data available for formatting")
        return "No company data available. Generate summaries first."
    
    logger.info(f"Formatting data for {len(data)} companies")
    
    # Return the raw data for processing in the UI
    return data

def get_formatted_company_markdown(data):
    """Convert the company data to a markdown table"""
    if not data or not isinstance(data, list):
        return "No company data available. Generate summaries first."
        
    formatted_output = "# Company CHRO Data\n\n"
    formatted_output += "| Company | CHRO Name | LinkedIn URL | Timestamp |\n"
    formatted_output += "|---------|-----------|--------------|------------|\n"
    
    for item in data:
        company = item.get('company', 'Unknown')
        name = item.get('name', 'Not available')
        linkedin_url = item.get('linkedin_url', 'Not available')
        timestamp = item.get('timestamp', 'Unknown')
        
        # Format URL as markdown link if available
        linkedin_display = f"[Profile]({linkedin_url})" if linkedin_url != "Not available" else "Not available"
        
        formatted_output += f"| {company} | {name} | {linkedin_display} | {timestamp} |\n"
    
    return formatted_output

def fix_final_summaries_file():
    """Attempt to fix the final_summaries.json file by converting it to a proper JSON array"""
    try:
        # Get the absolute path of the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, 'final_summaries.json')
        
        # Check for file existence
        if not os.path.exists(file_path):
            # Try current working directory as fallback
            cwd_path = os.path.join(os.getcwd(), 'final_summaries.json')
            if os.path.exists(cwd_path):
                file_path = cwd_path
            else:
                logger.warning(f"final_summaries.json not found at {file_path} or {cwd_path}")
                return False
        
        # Create a backup of the original file
        backup_path = file_path + '.original'
        if not os.path.exists(backup_path):
            import shutil
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created original backup at {backup_path}")
        
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if content.strip().startswith('[') and content.strip().endswith(']'):
            logger.info("File is already in JSON array format")
            return True
            
        # Find all JSON objects in the file
        pattern = r'\{[^{]*?\}'
        json_matches = re.findall(pattern, content, re.DOTALL)
        
        logger.info(f"Found {len(json_matches)} potential JSON objects")
        
        # Parse each JSON object
        extracted_objects = []
        for json_str in json_matches:
            try:
                data = json.loads(json_str)
                # Ensure we have all the required fields
                if 'Company' in data and 'Final_Summary' in data:
                    extracted_objects.append(data)
                    logger.info(f"Successfully parsed object for company: {data.get('Company')}")
            except json.JSONDecodeError:
                logger.warning(f"Error decoding JSON object: {json_str[:50]}...")
                continue
            except Exception as e:
                logger.error(f"Error processing object: {str(e)}")
                continue
        
        if not extracted_objects:
            logger.warning("No valid objects extracted, cannot fix file")
            return False
        
        # Create a backup of the current file
        backup_path = file_path + '.bak'
        import shutil
        shutil.copy2(file_path, backup_path)
        
        # Create a new file with proper JSON array format
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(extracted_objects, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Successfully fixed final_summaries.json and saved backup to {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Error fixing final_summaries.json: {str(e)}")
        return False

if __name__ == "__main__":
    # When run directly, extract and save the data
    data = extract_company_data()
    if data:
        save_extracted_data(data)
        print(f"Successfully extracted data for {len(data)} companies")
    else:
        print("No data extracted")
