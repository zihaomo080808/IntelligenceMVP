import logging
import json
import httpx
from typing import Dict, Any, Optional, List
from config import settings

# Configure logging
logger = logging.getLogger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

USER_PROFILE_SCHEMA = {
    "username": "string",
    "location": "string",
    "bio": "string"
}

async def query_user_background(db_messages: List[str]) -> dict:
    try:
        # Create prompt for the API
        prompt = f"""
        You are a helpful AI assistant responsible for extracting structured user profile information from a conversation during onboarding and for helping do an internet online person search.
        The user has provided information about their name, background, and interests below these instructions. First, extract all possible information and format it according to the following schema:

        {json.dumps(USER_PROFILE_SCHEMA, indent=2)}

        Follow these rules:
        1. For fields where no information is provided, use null.
        2. Make reasonable inferences for ambiguous information but don't invent facts.
        3. For username, extract only their first name if possible (not their full name).
        4. For location, extract the most detailed location information available.
        5. Keep all responses concise.

        Then, for the "bio" field, search on the internet and generate a 5-6 sentence personal bio for a person who has the profile you have extracted.
        I want the bio to be accurate and comprehensive to the point that any info the person logs online it will be included. You do not have to use complete sentences, output in the most efficient but still understandable way (example format: time, experience, location, results with data, important details).

        Respond with ONLY a valid JSON object - no explanations or additional text.
        """
        
        # Prepare the API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}"
        }
        
        payload = {
            "model": "sonar-pro",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that creates professional, factual user bios based on profile information."},
                {"role": "user", "content": prompt + "\n\n" + "\n".join(db_messages)}
            ],
        }

        logger.info(f"Sending query to Perplexity API for onboarding profile extraction")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                PERPLEXITY_API_URL,
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"Perplexity API error line 74 perplexity_client.py: {response.status_code} - {response.text}")
                return {}
                
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            logger.info(f"Generated profile extraction response ({len(content)} chars)")
            try:
                profile_data = json.loads(content)
                return profile_data
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON from Perplexity: {e}")
                return {}
    except Exception as e:
        logger.error(f"Error querying Perplexity API line 84 perplexity_client.py: {str(e)}")
        return {}