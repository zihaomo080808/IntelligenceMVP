import logging
from supabase import create_client, Client
from config import settings

logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    """
    Create and return a Supabase client using configuration from settings
    """
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        return supabase
    except Exception as e:
        logger.error(f"Error creating Supabase client: {str(e)}")
        raise