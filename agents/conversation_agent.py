import openai
from config import settings
from database.supabase import get_supabase_client
from agents.system_prompts import ALEX_HEFLE_PROMPT, RECOMMENDATION_PROMPT
from matcher.recommendation_engine import recommend_to_user, record_recommendation, secondary_recommend
from twilio.rest import Client
import asyncio
import logging
import json
import requests
from datetime import datetime, timezone
import re
from profiles.profiles import update_user_profile
from agents.callgpt import call_gpt, get_embedding

logger = logging.getLogger(__name__)

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
twilio_number = settings.TWILIO_PHONE_NUMBER

redis_client = settings.redis_client

async def record_message(active_conversation, user_message, message_to_process):
    supabase = get_supabase_client()
    updated_messages = active_conversation.get('messages', [])
    updated_messages.extend([
        {"sender": "user", "content": message_to_process, "timestamp": datetime.now(timezone.utc)},
        {"sender": "system", "content": user_message, "timestamp": datetime.now(timezone.utc)}
    ])
    supabase.table('user_conversations').update({
        'messages': updated_messages
    }).eq('id', active_conversation['id']).execute()

async def converse_with_user(user_id: str, message) -> str:
    # If message is a list, join with '\n'
    if isinstance(message, list):
        message_to_process = '\n'.join(message)
    else:
        message_to_process = message
    # Get conversation history directly from user_conversations
    supabase = get_supabase_client()
    
    # Fetch user profile
    user_profile_response = supabase.table('profiles').select('*').eq('user_id', user_id).single().execute()
    user_profile = user_profile_response.data if user_profile_response and user_profile_response.data else None
    if user_profile and 'embedding' in user_profile:
        user_profile = {k: v for k, v in user_profile.items() if k != 'embedding'}
    
    # Get or create active conversation
    active_conv_response = supabase.table('user_conversations').select('*').eq('user_id', user_id).is_('ended_at', 'null').order('started_at', desc=True).limit(1).execute()
    
    if not active_conv_response.data:
        # Create new conversation
        new_conv = {
            'user_id': user_id,
            'started_at': datetime.now(timezone.utc),
            'messages': []
        }
        active_conv_response = supabase.table('user_conversations').insert(new_conv).execute()
        if not active_conv_response.data:
            logger.error(f"Failed to create new conversation for user {user_id}")
            return "Sorry, I'm having trouble starting our conversation. Please try again."
    
    active_conversation = active_conv_response.data[0]
    messages = active_conversation.get('messages', [])
    
    # Get last recommendation (most recent by created_at)
    last_rec_response = supabase.table('user_recommendations').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(1).execute()
    
    # Instead, fetch from recent_recommendations table
    recs_response = supabase.table('recent_recommendations').select('recommendations').eq('user_id', user_id).single().execute()
    recs = recs_response.data['recommendations'] if recs_response and recs_response.data and recs_response.data.get('recommendations') else []
    if not recs or not isinstance(recs, list) or len(recs) == 0:
        logger.info(f"No recommendations found for user {user_id}")
        return "Hey! I'm having trouble finding opportunities that match your interests right now. Want to chat about something else?"

    # Format conversation history from messages
    conversation_history = []
    for msg in messages:
        role = "assistant" if msg['sender'] == 'system' else "user"
        conversation_history.append({"role": role, "content": msg['content']})

    # Format last recommendation
    last_recommendation = None
    if last_rec_response.data and last_rec_response.data[0]:
        last_rec = last_rec_response.data[0]
        # Get the full opportunity details
        opp_response = supabase.table('opportunities').select('*').eq('id', last_rec['item_id']).single().execute()
        if opp_response.data:
            last_recommendation = {
                "id": last_rec['item_id'],
                "title": opp_response.data.get('title'),
                "description": opp_response.data.get('description'),
                "details": opp_response.data.get('details', {}),
                "recommended_at": last_rec['created_at'],
                "status": last_rec['status']
            }

    # Format current recommendations
    current_recommendation = []
    for rec in recs[:5]:  # Only include top 1
        current_recommendation.append({
            "id": rec['id'],
            "title": rec.get('title'),
            "description": rec.get('description'),
            "details": rec.get('details', {}),
            "score": rec.get('distance', 0),
            "tags": rec.get('tags', [])
        })

    context = {
        "conversation_history": conversation_history,
        "last_recommendation": last_recommendation,
        "current_recommendations": current_recommendation,
        "user_profile": user_profile
    }
    messages = [
        {"role": "system", "content": ALEX_HEFLE_PROMPT},
        {"role": "system", "content": f"Context for this conversation:\n{json.dumps(context, indent=2)}"},
    ]
    
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": message_to_process})

    # Call GPT
    response = await call_gpt(messages, model="o4-mini")
    
    gpt_response = response.choices[0].message.content.strip()
    user_message = None
    json_match = re.match(r'\{[\s\S]*\}$', gpt_response)
    if json_match:
        try:
            gpt_json = json.loads(gpt_response)
            # 1. Old opportunities format: has 'id' and 'message'
            if isinstance(gpt_json, dict) and 'id' in gpt_json and 'message' in gpt_json:
                user_message = gpt_json['message']
                # Record the opportunity as given to the user
                record_recommendation(user_id, gpt_json['id'], 1.0)
            # 2. New RAG format: third dict has 'type': 'RAG' and second dict is tags (list)
            elif (
                isinstance(gpt_json, dict) and
                isinstance(list(gpt_json.values()), list) and
                len(list(gpt_json.values())) >= 3 and
                isinstance(list(gpt_json.values())[2], str) and
                list(gpt_json.values())[2].upper() == 'RAG' and
                isinstance(list(gpt_json.values())[1], list)
            ):
                modified_user_message = list(gpt_json.values())[0]
                tags = list(gpt_json.values())[1]
                user_message = await secondary_recommend(user_id, modified_user_message, tags)
            # 3. New RAG format: second dict has 'type': 'RAG' (no tag filtering)
            elif (
                isinstance(gpt_json, dict) and
                isinstance(list(gpt_json.values()), list) and
                len(list(gpt_json.values()) )>= 2 and
                isinstance(list(gpt_json.values())[1], str) and
                list(gpt_json.values())[1].upper() == 'RAG'
            ):
                modified_user_message = list(gpt_json.values())[0]
                user_message = await secondary_recommend(user_id, modified_user_message, None)
            # 4. Profile update: has 'type': 'UPDATE'
            elif gpt_json.get('type', '').upper() == 'UPDATE':
                user_message = gpt_json.get('message', user_message)
                profile_updates = {k: v for k, v in gpt_json.items() if k not in ['message', 'type']}
                if profile_updates:
                    embedding_fields = []
                    for field in ['bio', 'username', 'location']:
                        if field in profile_updates and profile_updates[field]:
                            embedding_fields.append(profile_updates[field])
                    if embedding_fields:
                        embedding_input = ' '.join(embedding_fields)
                        embedding = await get_embedding(embedding_input)
                        if embedding:
                            profile_updates['embedding'] = embedding
                    if user_profile:
                        merged_profile = user_profile.copy()
                        merged_profile.update(profile_updates)
                        await update_user_profile(user_id, merged_profile)
                    else:
                        await update_user_profile(user_id, profile_updates)
        except Exception as e:
            logger.error(f"Failed to parse/update profile or RAG JSON: {e}")

    # Update conversation with new messages
    await record_message(active_conversation, user_message, message_to_process)
    return user_message

async def send_daily_recommendation(user_id):
    recs = await recommend_to_user(user_id)
    if not recs or not isinstance(recs, list) or len(recs) == 0:
        logger.info(f"No recommendations found for user {user_id}")
        return
    top_rec = recs[0]
    # Record the top recommendation only here
    record_recommendation(user_id, top_rec['id'], top_rec.get('score', 0))
    message = f"Hey! Based on your profile, here's something you might like: {top_rec['title']} - {top_rec['description']}"
    # Use the send_sms endpoint to queue the message
    payload = {
        'to': user_id,
        'message': message
    }
    url = settings.SEND_SMS_URL if hasattr(settings, 'SEND_SMS_URL') else 'http://localhost:5000/send/sms'
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logger.info(f"Queued daily recommendation to {user_id}: {top_rec['id']}")
        else:
            logger.error(f"Failed to queue SMS for {user_id}: {response.text}")
    except Exception as e:
        logger.error(f"Exception when calling send_sms endpoint: {e}")

# Example usage (for testing only):
# import asyncio
# print(asyncio.run(converse_with_user("+1234567890", "Hello!")))

# Example usage for Railway cron job:
# import asyncio
# asyncio.run(send_daily_recommendation('+1234567890')) 