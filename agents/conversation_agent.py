import openai
from config import settings
from database.supabase import get_supabase_client
from agents.system_prompts import ALEX_HEFLE_PROMPT
from matcher.recommendation_engine import recommend_to_user
from twilio.rest import Client
import asyncio
import logging
import json
import requests

logger = logging.getLogger(__name__)

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
twilio_number = settings.TWILIO_PHONE_NUMBER

redis_client = settings.redis_client
MESSAGING_QUEUE_NAME = 'twilio_messages'

async def converse_with_user(user_id: str, message: str) -> str:
    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    response = await client.chat.completions.create(
        model="o4-mini",
        messages=[
            {"role": "system", "content": ALEX_HEFLE_PROMPT},
            {"role": "user", "content": message}
        ],
    )
    return response.choices[0].message.content.strip()

async def send_daily_recommendation(user_id):
    recs = await recommend_to_user(user_id)
    if not recs or not isinstance(recs, list) or len(recs) == 0:
        logger.info(f"No recommendations found for user {user_id}")
        return
    top_rec = recs[0]
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