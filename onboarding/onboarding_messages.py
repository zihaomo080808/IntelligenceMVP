import logging
import json
import os
from typing import Dict, Any, Optional, List, Union
from openai import AsyncOpenAI
from config import settings
from database.models import UserProfile
from database.supabase import get_supabase_client
from profiles.profiles import get_user_profile, create_user_profile, update_user_profile
from perplexity_client import query_user_background

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
logger.info(f"OPENAI_API_KEY set?: {bool(settings.OPENAI_API_KEY)}")
logger.info(f"OPENAI_API_KEY length: {len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0}")

try:
    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=20.0
    )
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {str(e)}")
    # Create the client anyway - we'll handle errors during the API call
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Define the user profile schema - adjust as needed for your application
USER_PROFILE_SCHEMA = {
    "username": "string",  # Changed from "name" to "username" to match database field
    "location": "string",
    "education": "string",
    "occupation": "string",
    "current_projects": "list_of_strings",
    "interests": "list_of_strings",
    "skills": "list_of_strings",
    "goals": "list_of_strings",
    "bio": "string"
}

# System prompt for information extraction
SYSTEM_PROMPT = f"""
You are a helpful AI assistant responsible for extracting structured user profile information from a conversation during onboarding.
The user has provided information about their name, background, and interests. Extract all possible information and format it according to the following schema:

{json.dumps(USER_PROFILE_SCHEMA, indent=2)}

Follow these rules:
1. For fields where no information is provided, use null.
2. Make reasonable inferences for ambiguous information but don't invent facts.
3. For username, extract only their first name if possible (not their full name).
4. For location, extract the most detailed location information available.
5. For list fields, include all relevant items mentioned.
6. Keep all responses concise.

Respond with ONLY a valid JSON object - no explanations or additional text.
"""

async def extract_profile_info(accumulated_messages: List[str]) -> Dict[str, Any]:
    try:
        # Combine all messages into a single context
        combined_context = "\n".join([
            f"Message {i+1}: {msg}" for i, msg in enumerate(accumulated_messages)
        ])
        
        logger.info(f"Extracting profile info from accumulated messages: {combined_context[:100]}...")

        response = await client.chat.completions.create(
            model=settings.CLASSIFIER_MODEL or "gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": combined_context}
            ],
        )
        
        # Extract the response
        content = response.choices[0].message.content.strip()
        logger.info(f"Received extraction response onboarding_messages line 85 (first 100 chars): {content[:100]}...")
        
        try:
            profile_data = json.loads(content)
            logger.info(f"Successfully parsed profile data with {len(profile_data)} fields")
            return profile_data
        except json.JSONDecodeError as json_err:
            logger.error(f"Error parsing JSON from API response: {str(json_err)}")
            # Try to extract just the JSON part if there's extra text
            if '{' in content and '}' in content:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                json_content = content[json_start:json_end]
                try:
                    profile_data = json.loads(json_content)
                    logger.info(f"Successfully parsed profile data after cleanup with {len(profile_data)} fields")
                    return profile_data
                except:
                    pass
            
            # Return empty result if parsing fails
            return {}
        
    except Exception as e:
        logger.error(f"Error extracting profile info (onboarding_messages line 109): {str(e)}")
        return {}

async def process_onboarding_message(
    message: str,
    step: int,
    phone_number: str,
    current_profile: Dict[str, Any] = None,
    accumulated_messages: List[str] = None
) -> tuple[Dict[str, Any], str, bool]:
    try:
        supabase = get_supabase_client()
        state_response = supabase.table('user_states').select('accumulated_messages').eq('phone_number', phone_number).execute()
        
        if not state_response.data:
            logger.error(f"No state found for user {phone_number}, either error in database fetch or user state not created (error in twilio_routes.py onboarding)")
            return current_profile, "Sorry, I encountered an error. Please try again.", False
            
        # Get accumulated messages from the database
        db_messages = state_response.data[0].get('accumulated_messages', [])
        if not isinstance(db_messages, list):
            db_messages = []
            
        # Add current message to accumulated messages
        db_messages.append(message)
        
        # Update the accumulated messages in the database
        supabase.table('user_states').update({
            'accumulated_messages': db_messages
        }).eq('phone_number', phone_number).execute()
        
        if step == 2:
            extracted_info = await extract_profile_info(db_messages)
            logger.info(f"Extracted info: {extracted_info}")
            
            # Update profile with extracted information
            updated_profile = {**current_profile, **extracted_info}
            
            # Generate bio using Perplexity
            bio = await query_user_background(updated_profile)
            if bio:
                updated_profile['bio'] = bio
            
            # Generate embedding
            if updated_profile.get('bio'):
                embedding = await get_embedding(updated_profile['bio'])
                if embedding:
                    updated_profile['embedding'] = embedding
            updated_profile['user_id'] = phone_number

            try:
                existing_profile = await get_user_profile(phone_number)
                
                if existing_profile:
                    # Update existing profile
                    existing_profile = await update_user_profile(phone_number, updated_profile)
                else:
                    # Create new profile
                    existing_profile = await create_user_profile(updated_profile)
                    
                logger.info(f"Profile saved to Supabase for user {phone_number}")
            except Exception as db_error:
                import traceback
                db_stack_trace = traceback.format_exc()
                logger.error(f"Error saving profile to Supabase: {str(db_error)}")
                logger.error(f"Database operation stack trace: {db_stack_trace}")
                # Continue even if database save fails, but log comprehensive information
            
            return updated_profile, "Thanks for sharing all this information! Your profile is now complete.", True
        
        # For non-final steps, just return the current profile and next question
        next_question = ""
        if step == 0:  # After username
            next_question = "Great! Could you tell me a bit about your background? Where are you from, what's your education, and what do you do?"
        elif step == 1:  # After background
            next_question = "Thanks! What are your main interests and what kind of opportunities are you looking for?"
        
        return current_profile, next_question, False
        
    except Exception as e:
        logger.error(f"Error processing onboarding message: {str(e)}")
        return current_profile, "Sorry, I encountered an error. Please try again.", False

async def get_embedding(text: str) -> List[float]:
    """Get embedding for text using OpenAI"""
    try:
        response = await client.embeddings.create(
            model=settings.EMBEDDING_MODEL or "text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error getting embedding: {str(e)}")
        return None

# Function for parsing the username from a greeting message (first message)
async def extract_name_from_greeting(message: str) -> str:
    """
    Extract just the username from a greeting message
    
    Args:
        message: The user's first message
        
    Returns:
        Extracted username or empty string
    """
    extracted_info = await extract_profile_info([message])
    return extracted_info.get('username', '')