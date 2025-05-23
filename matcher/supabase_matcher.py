import os
from supabase import create_client, Client
from config import settings 

# Initialize Supabase client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

def match_opportunities(
    user_id,
    embedding,  # list of 1536 floats
    top_k=5,
    deadline_before=None,
):
    params = {
        "p_user_id": user_id,
        "p_embedding": embedding,
        "p_top_k": top_k,
        "p_deadline_before": deadline_before,
    }
    # Remove None values (Supabase RPC doesn't like them)
    params = {k: v for k, v in params.items() if v is not None}
    # Call the RPC function
    result = supabase.rpc("match_opportunities", params).execute()
    return result.data

# Example usage:
# matches = match_opportunities(user_id, user_embedding, top_k=5)