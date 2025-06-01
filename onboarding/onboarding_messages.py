import logging
from typing import Dict, Any, Optional, List, Union
from config import settings
from database.supabase import get_supabase_client
from profiles.profiles import get_user_profile, create_user_profile, update_user_profile
from agents.perplexity_client import query_user_background
from profiles.profiles import get_embedding

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def process_onboarding_message(
    message,  # Accept list or string
    step: int,
    phone_number: str,
    current_profile: Dict[str, Any] = None,
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
            
        # If message is a list, join with '\n'
        if isinstance(message, list):
            message_to_store = '\n'.join(message)
        else:
            message_to_store = message
        
        # Add current message to accumulated messages
        db_messages.append(message_to_store)
        
        # Update the accumulated messages in the database
        supabase.table('user_states').update({
            'accumulated_messages': db_messages
        }).eq('phone_number', phone_number).execute()
        
        if step == 2:
            extracted_info = await query_user_background(db_messages)
            logger.info(f"Extracted info: {extracted_info}")

            updated_profile = {**current_profile, **extracted_info}
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
        if step == 0: 
            next_question = "Great! Could you tell me a bit about your background? Where are you from, what's your education, and what do you do?"
        elif step == 1: 
            next_question = "Thanks! What are your main interests and what kind of opportunities are you looking for?"
        
        return current_profile, next_question, False
        
    except Exception as e:
        logger.error(f"Error processing onboarding message: {str(e)}")
        return current_profile, "Sorry, I encountered an error. Please try again.", False