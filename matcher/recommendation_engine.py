from matcher.supabase_matcher import match_opportunities
from database.supabase import get_supabase_client
from agents.conversation_agent import converse_with_user
from datetime import datetime, timezone

# Helper to get user embedding (implement as needed)
def get_user_embedding(user_id):
    supabase = get_supabase_client()
    response = supabase.table('profiles').select('embedding').eq('user_id', user_id).limit(1).execute()
    if response.data and response.data[0].get('embedding'):
        return response.data[0]['embedding']
    return None

# Record a recommendation in user_recommendations
def record_recommendation(user_id, item_id, score):
    supabase = get_supabase_client()
    supabase.table('user_recommendations').insert({
        'user_id': user_id,
        'item_id': item_id,
        'recommended_score': score,
        'status': 'sent',
        'created_at': datetime.now(timezone.utc)
    }).execute()

# Main orchestration function
async def recommend_to_user(user_id, filters=None):
    embedding = get_user_embedding(user_id)
    if not embedding:
        return "Sorry, we couldn't find your profile embedding line 29 recommendation_engine.py"

    recs = match_opportunities(user_id, embedding, **(filters or {}))
    if not recs:
        return "Sorry, no new opportunities found for you right now line 33 recommendation_engine.py."
    # 2. Record recommendations
    top_rec = recs[0]
    record_recommendation(user_id, top_rec['id'], top_rec.get('distance', 0))
    # 4. Optionally, personalize with conversation agent
    return recs