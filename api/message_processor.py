import asyncio
import logging
from twilio.rest import Client
from config import settings
from twilio_routes import process_message, handle_onboarding
from database.models import UserConversation
from database.supabase import get_supabase_client
from datetime import datetime, timezone
import json
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
twilio_number = settings.TWILIO_PHONE_NUMBER

redis_client = settings.redis_client

def process_queued_messages(queue_name='twilio_messages'):
    while True:
        try:
            # Get the oldest message from the queue
            message_data = redis_client.rpop(queue_name)
            if message_data:
                data = json.loads(message_data)
                
                if data.get('is_outbound'):
                    client.messages.create(
                        body=data['message'],
                        from_=twilio_number,
                        to=data['phone_number']
                    )
                    logger.info(f"Sent message to {data['phone_number']}")
                else:
                    loop = asyncio.new_event_loop()
                    response = loop.run_until_complete(process_message(data['phone_number'], data['message']))
                    loop.close()
                    store_message(data['phone_number'], 'user', data['message'])
                    # Send the response back to the user
                    client.messages.create(
                        body=response,
                        from_=twilio_number,
                        to=data['phone_number']
                    )
                    logger.info(f"Sent response to {data['phone_number']}")
        except Exception as e:
            logger.error(f"Error processing queued message: {str(e)}")
            continue

def process_onboarding_queue(queue_name='onboarding_queue'):
    while True:
        try:
            message_data = redis_client.rpop(queue_name)
            if message_data:
                data = json.loads(message_data)
                loop = asyncio.new_event_loop()
                response = loop.run_until_complete(handle_onboarding(data['phone_number'], data['message']))
                loop.close()
                client.messages.create(
                    body=response,
                    from_=twilio_number,
                    to=data['phone_number']
                )
                logger.info(f"Sent onboarding response to {data['phone_number']}")
        except Exception as e:
            logger.error(f"Error processing onboarding queued message: {str(e)}")
            continue

if __name__ == "__main__":
    # Choose which queue to process based on command-line argument
    if len(sys.argv) > 1 and sys.argv[1] == 'onboarding':
        process_onboarding_queue()
    else:
        process_queued_messages() 


def store_message(user_id, sender, content):
    supabase = get_supabase_client()
    now = datetime.now(timezone.utc)
    response = supabase.table('user_conversations').select('*').eq('user_id', user_id).order('started_at', desc=True).limit(1).execute()
    if response.data:
        convo = response.data[0]
        messages = convo.get('messages', [])
        messages.append({
            "sender": sender,
            "content": content,
            "timestamp": now.isoformat() + "Z"
        })
        supabase.table('user_conversations').update({"messages": messages, "ended_at": now}).eq('id', convo['id']).execute()
    else:
        messages = [{
            "sender": sender,
            "content": content,
            "timestamp": now.isoformat() + "Z"
        }]
        supabase.table('user_conversations').insert({
            "user_id": user_id,
            "messages": messages,
            "started_at": now,
            "ended_at": now
        }).execute()