import os
from supabase import create_client, Client
from config import settings 

# Initialize Supabase client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

def match_opportunities(user_id, embedding, top_k=5, tag=None, **kwargs):
    params = {
        "p_user_id": user_id,
        "p_embedding": embedding,
        "p_top_k": top_k
    }
    if tag:
        params["p_tag"] = tag
    return supabase.rpc("match_opportunities", params).execute().data

# Example usage:
# matches = match_opportunities(user_id, user_embedding, top_k=5)