from google import genai
from google.genai import types
import logging
from typing import Dict, Any
import re

logger = logging.getLogger(__name__)

class GeminiDirectSearcher:
    def __init__(self, api_key: str):
        """Initialize with API key"""
        self.api_key = api_key
        self.client = self._configure_gemini_client()

    def _configure_gemini_client(self):
        """Configure and return a Gemini API client"""
        return genai.Client(api_key=self.api_key)

    def _create_search_tool(self, threshold: float = 0.3):
        """
        Create a Google Search tool with dynamic retrieval configuration
        
        Args:
            threshold (float): Dynamic threshold value between 0 and 1
                            Lower values mean more queries use search grounding
        """
        return types.Tool(
            google_search=types.GoogleSearchRetrieval(
                dynamic_retrieval_config=types.DynamicRetrievalConfig(
                    dynamic_threshold=threshold
                )
            )
        )

    def _extract_name(self, text: str) -> str:
        """
        Extract just the name from the response text.
        Removes any additional information like titles, positions, etc.
        """
        # Remove common prefixes/titles
        text = re.sub(r'^(The |Current |Present |As of \d{4}, |Mr\. |Ms\. |Mrs\. |Dr\. )', '', text, flags=re.IGNORECASE)
        
        # Remove position information
        text = re.sub(r'(is |was |serves as |working as |the |current |CHRO|Chief Human Resources? Officer|HR Head|Head of HR|VP of HR|Senior VP)[^.]*', '', text, flags=re.IGNORECASE)
        
        # Get the first line only
        text = text.split('\n')[0].strip()
        
        # Get the first sentence only
        text = text.split('.')[0].strip()
        
        # Remove any text in parentheses
        text = re.sub(r'\([^)]*\)', '', text)
        
        # Clean up any remaining special characters and extra spaces
        text = re.sub(r'[^\w\s-]', '', text)
        text = ' '.join(text.split())
        
        return text

    def _generate_grounded_response(self, prompt: str, model_id: str = "gemini-2.0-flash", threshold: float = 0.3) -> Dict[str, Any]:
        """
        Generate a response using Gemini with Google Search grounding
        
        Args:
            prompt (str): User's question or prompt
            model_id (str): Gemini model to use
            threshold (float): Dynamic threshold for search grounding
        
        Returns:
            dict: Response content and grounding metadata
        """
        try:
            response = self.client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[self._create_search_tool(threshold)],
                    response_modalities=["TEXT"],
                )
            )
            
            # Initialize result with default values
            result = {
                'response_text': '',
                'raw_response': '',
                'sources': []
            }
            
            # Extract response text if available
            if (hasattr(response, 'candidates') and 
                response.candidates and 
                hasattr(response.candidates[0], 'content') and 
                response.candidates[0].content.parts):
                raw_text = response.candidates[0].content.parts[0].text
                cleaned_name = self._extract_name(raw_text)
                result['response_text'] = cleaned_name
                result['raw_response'] = raw_text
            
            # Extract grounding metadata if available
            if (hasattr(response, 'candidates') and 
                response.candidates and 
                hasattr(response.candidates[0], 'grounding_metadata') and 
                response.candidates[0].grounding_metadata):
                
                metadata = response.candidates[0].grounding_metadata
                
                # Extract search suggestions if available
                if (hasattr(metadata, 'search_entry_point') and 
                    metadata.search_entry_point and 
                    hasattr(metadata.search_entry_point, 'rendered_content')):
                    result['search_suggestions'] = metadata.search_entry_point.rendered_content
                
                # Extract sources if available
                if (hasattr(metadata, 'grounding_chunks') and 
                    metadata.grounding_chunks is not None):
                    sources = []
                    for chunk in metadata.grounding_chunks:
                        if (hasattr(chunk, 'web') and 
                            chunk.web is not None and 
                            hasattr(chunk.web, 'uri') and 
                            hasattr(chunk.web, 'title')):
                            sources.append({
                                'uri': chunk.web.uri,
                                'title': chunk.web.title
                            })
                    result['sources'] = sources
            
            return result
        
        except Exception as e:
            logger.error(f"Error in generate_grounded_response: {str(e)}", exc_info=True)
            return {
                'error': str(e),
                'response_text': '',
                'raw_response': '',
                'sources': []
            }

    async def search(self, company_name: str, model_id: str = "gemini-2.0-flash", threshold: float = 0.3) -> Dict[str, Any]:
        """
        Search for CHRO/HR Head using Gemini's direct search
        
        Args:
            company_name (str): Name of the company to search for
            model_id (str): Gemini model to use
            threshold (float): Search grounding threshold
            
        Returns:
            Dict containing search results and metadata
        """
        try:
            prompt = (
                f"Who is the Chief Human Resource Officer (CHRO) of {company_name} India? "
                "Respond with ONLY the person's full name, nothing else. "
                "Do not include their title, position, or any other information. "
                "Example response format: 'John Smith'"
            )
            
            result = self._generate_grounded_response(prompt, model_id, threshold)
            
            if 'error' in result:
                logger.error(f"Error in Gemini search: {result['error']}")
                return {
                    'error': result['error'],
                    'response_text': '',
                    'raw_response': '',
                    'sources': []
                }
            
            logger.info(f"Gemini search result: {result}")
            return {
                'response_text': result.get('response_text', ''),
                'raw_response': result.get('raw_response', ''),
                'sources': result.get('sources', [])
            }
            
        except Exception as e:
            logger.error(f"Error in Gemini direct search: {str(e)}", exc_info=True)
            return {
                'error': str(e),
                'response_text': '',
                'raw_response': '',
                'sources': []
            } 
            
    async def generate_summary(self, 
                        company_name: str, 
                        perplexity_result: str, 
                        openai_result: str, 
                        google_result: str, 
                        linkedin_result: str, 
                        model_id: str = "gemini-1.5-flash") -> Dict[str, Any]:
        """
        Generate a comprehensive summary from multiple data sources using Gemini
        
        Args:
            company_name (str): Name of the company
            perplexity_result (str): Results from Perplexity search
            openai_result (str): Results from OpenAI/ChatGPT search
            google_result (str): Results from Google/Gemini search
            linkedin_result (str): Results from LinkedIn search
            model_id (str): Gemini model to use for summary generation
            
        Returns:
            Dict containing the summary and metadata
        """
        try:
            # Format the input data
            formatted_data = f"""
Source 1 (Perplexity AI): {perplexity_result}

Source 2 (OpenAI): {openai_result}

Source 3 (Google Search): {google_result}

Source 4 (LinkedIn Head Search): {linkedin_result}
"""
            
            # Create the summary prompt
            summary_prompt = f"""Act as a professional HR data analyst. I have gathered information about the CHRO (Chief Human Resources Officer) of {company_name} from four different AI sources. Here is the verified data:

{formatted_data}

Based on these sources, please provide a comprehensive profile with these sections:

1. Executive Summary:
   - Full Name and Current Position
   - Confirmation of Role at {company_name}
   - Direct LinkedIn Profile URL (if available)

2. Professional Background:
   - Previous positions and companies
   - Years of experience in HR
   - Educational background (if available)

3. Current Role at {company_name}:
   - Key responsibilities
   - Notable initiatives or transformations led
   - Areas of focus

4. Source Analysis:
   - Comparison of information from all sources
   - Confidence level in the information
   - Any discrepancies found

Format as a clean, professional profile with bullet points and clear sections. Ensure the output is well-structured and directly answers the question about who is the CHRO at {company_name}."""
            
            # Use a different method to generate content since we're not using search grounding
            try:
                model = self.client.models.get(model_id)
                response = model.generate_content(summary_prompt)
                
                # Extract the summary text
                summary_text = ''
                if hasattr(response, 'candidates') and response.candidates:
                    if hasattr(response.candidates[0], 'content') and response.candidates[0].content.parts:
                        summary_text = response.candidates[0].content.parts[0].text
                
                logger.info(f"Generated summary for {company_name}")
                
                return {
                    'summary': summary_text,
                    'company': company_name,
                    'model_used': model_id,
                    'error': None
                }
                
            except Exception as e:
                logger.error(f"Error generating summary with Gemini: {str(e)}", exc_info=True)
                return {
                    'summary': '',
                    'company': company_name,
                    'model_used': model_id,
                    'error': str(e)
                }
                
        except Exception as e:
            logger.error(f"Error in generate_summary: {str(e)}", exc_info=True)
            return {
                'summary': '',
                'company': company_name,
                'error': str(e)
            } 