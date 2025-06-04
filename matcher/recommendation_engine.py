from matcher.supabase_matcher import match_opportunities
from database.supabase import get_supabase_client
import openai
from datetime import datetime, timezone
from agents.system_prompts import ANTICIPATORY_DAILY_PROMPT
import json
from matcher.tags import TAGS
from config import settings
from agents.callgpt import call_gpt, get_embedding

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
async def recommend_to_user(user_id, filters=None, top_k=5):
    supabase = get_supabase_client()
    # 1. Fetch recent user conversation (last 10 messages)
    convo_response = supabase.table('user_conversations').select('messages').eq('user_id', user_id).order('started_at', desc=True).limit(1).execute()
    recent_messages = []
    if convo_response.data and convo_response.data[0].get('messages'):
        recent_messages = convo_response.data[0]['messages']

    # 2. Call OpenAI with anticipatory prompt
    prompt = ANTICIPATORY_DAILY_PROMPT
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "\n".join(recent_messages)}
    ]
    gpt_response = await call_gpt(messages, model="o4-mini")
    anticipation_json = gpt_response.choices[0].message.content.strip()
    tag = None
    anticipation_data = None
    try:
        anticipation_data = json.loads(anticipation_json)
        tag = anticipation_data.get('tag')
        if tag not in TAGS:
            tag = None
    except Exception:
        anticipation_data = {"description": anticipation_json}
    # 3. Generate embedding for GPT output (use description if available)
    embedding_input = anticipation_data.get('description') if anticipation_data and 'description' in anticipation_data else anticipation_json
    embedding = await get_embedding(embedding_input)
    if not embedding:
        return anticipation_data, []
    # 4. Call Supabase RPC to match opportunities, filtering by tag if available
    recs = match_opportunities(user_id, embedding, top_k=top_k, tag=tag, **(filters or {}))
    if not recs:
        return anticipation_data, []
    # 6. Store the rest of the recs (except the first) in recent_recommendations table (up to last 4)
    if len(recs) > 1:
        supabase = get_supabase_client()
        # Get existing recent recommendations
        response = supabase.table('recent_recommendations').select('recommendations').eq('user_id', user_id).single().execute()
        existing = response.data['recommendations'] if response and response.data and response.data.get('recommendations') else []
        # Append new recs (excluding the first/top rec)
        new_recs = recs[1:]
        combined = existing + new_recs
        # Keep only the last 4
        combined = combined[-4:]
        # Upsert (insert or update)
        supabase.table('recent_recommendations').upsert({
            'user_id': user_id,
            'recommendations': combined,
            'created_at': datetime.now(timezone.utc)
        }).execute()

    return recs

async def secondary_recommend(user_id, message, tags, filters=None, top_k=5):
    supabase = get_supabase_client()
    # 1. Fetch recent user conversation (last 10 messages)
    embedding = await get_embedding(message)
    if not embedding:
        return None, []
    # 4. Call Supabase RPC to match opportunities, filtering by tag if available
    recs = match_opportunities(user_id, embedding, top_k=top_k, tag=tags, **(filters or {}))
    if not recs:
        return None, []
    # 6. Store the rest of the recs (except the first) in recent_recommendations table (up to last 4)
    if len(recs) > 1:
        supabase = get_supabase_client()
        # Get existing recent recommendations
        response = supabase.table('recent_recommendations').select('recommendations').eq('user_id', user_id).single().execute()
        existing = response.data['recommendations'] if response and response.data and response.data.get('recommendations') else []
        # Append new recs (excluding the first/top rec)
        new_recs = recs[1:]
        combined = existing + new_recs
        # Keep only the last 4
        combined = combined[-4:]
        # Upsert (insert or update)
        supabase.table('recent_recommendations').upsert({
            'user_id': user_id,
            'recommendations': combined,
            'created_at': datetime.now(timezone.utc)
        }).execute()

    return recs
