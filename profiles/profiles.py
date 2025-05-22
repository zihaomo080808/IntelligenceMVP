import logging
from typing import Dict, Any, Optional, List, Union
from database.supabase import get_supabase_client
from database.models import UserProfile, UserState
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

async def get_user_profile(phone_number: str) -> Optional[UserProfile]:

    try:
        supabase = get_supabase_client()
        response = supabase.table('profiles').select('*').eq('user_id', phone_number).execute()
        
        if not response.data:
            logger.info(f"No profile found for user {phone_number}")
            return None
            
        return UserProfile.from_supabase_dict(response.data[0])
    except Exception as e:
        logger.error(f"Error retrieving user profile: {str(e)}")
        return None

async def create_user_profile(profile_data: Dict[str, Any]) -> Optional[UserProfile]:
    try:
        supabase = get_supabase_client()
        # Create a UserProfile instance
        profile = UserProfile(**profile_data)
        # Convert to dict for Supabase
        supabase_data = profile.to_supabase_dict()
        response = supabase.table('profiles').insert(supabase_data).execute()
        
        if not response.data:
            logger.error("No data returned after profile creation")
            return None
            
        return UserProfile.from_supabase_dict(response.data[0])
    except Exception as e:
        logger.error(f"Error creating user profile (profiles.profiles.py line 38): {str(e)}")
        return None

async def update_user_profile(phone_number: str, profile_data: Dict[str, Any]) -> Optional[UserProfile]:
    try:
        supabase = get_supabase_client()
        # Create a UserProfile instance with the phone number as user_id
        profile_data['user_id'] = phone_number
        profile_data['updated_at'] = datetime.now(timezone.utc)
        profile = UserProfile(**profile_data)
        supabase_data = profile.to_supabase_dict()
        
        # Update in Supabase
        response = supabase.table('profiles').update(supabase_data).eq('user_id', phone_number).execute()
        
        if not response.data:
            logger.error(f"No data returned after profile update for user {phone_number}")
            return None
            
        return UserProfile.from_supabase_dict(response.data[0])
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        return None
    
def merge_profile_updates(existing_profile: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    merged = existing_profile.copy()
    
    # Merge each field, handling null values and lists appropriately
    for key, value in new_data.items():
        # Skip null/None values
        if value is None:
            continue
            
        # Handle list fields
        if isinstance(value, list) and key in ['interests', 'skills', 'current_projects', 'goals']:
            # Initialize if not exists
            if key not in merged or not merged[key]:
                merged[key] = []
                
            # Add new items that don't already exist
            for item in value:
                if item and item not in merged[key]:
                    merged[key].append(item)
        # Handle string fields - only update if we have a value and the existing one is empty
        elif isinstance(value, str) and value.strip():
            if key not in merged or not merged[key]:
                merged[key] = value
    
    return merged

async def get_user_state(phone_number: str) -> Optional[UserState]:
    try:
        supabase = get_supabase_client()
        response = supabase.table('user_states').select('*').eq('phone_number', phone_number).execute()
        
        if not response.data:
            logger.info(f"No state found for user {phone_number}")
            return None
            
        return UserState.from_supabase_dict(response.data[0])
    except Exception as e:
        logger.error(f"Error retrieving user state: {str(e)}")
        return None

async def create_user_state(
    phone_number: str,
    step: int = 0,
    profile: Dict[str, Any] = None,
    accumulated_messages: List[str] = None
) -> Optional[UserState]:
    try:
        supabase = get_supabase_client()
        state = UserState(
            phone_number=phone_number,
            step=step,
            profile=profile or {},
            accumulated_messages=accumulated_messages or []
        )
        response = supabase.table('user_states').insert(state.to_supabase_dict()).execute()
        
        if not response.data:
            logger.error("No data returned after state creation")
            return None
            
        return UserState.from_supabase_dict(response.data[0])
    except Exception as e:
        logger.error(f"Error creating user state: {str(e)}")
        return None

async def update_user_state(phone_number: str, state_data: Dict[str, Any]) -> Optional[UserState]:
    try:
        supabase = get_supabase_client()
        state_data['updated_at'] = datetime.now(timezone.utc)
        
        response = supabase.table('user_states').update(state_data).eq('phone_number', phone_number).execute()
        
        if not response.data:
            logger.error(f"No data returned after state update for user {phone_number}")
            return None
            
        return UserState.from_supabase_dict(response.data[0])
    except Exception as e:
        logger.error(f"Error updating user state: {str(e)}")
        return None

async def delete_user_state(phone_number: str) -> bool:
    try:
        supabase = get_supabase_client()
        response = supabase.table('user_states').delete().eq('phone_number', phone_number).execute()
        return True
    except Exception as e:
        logger.error(f"Error deleting user state: {str(e)}")
        return False


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