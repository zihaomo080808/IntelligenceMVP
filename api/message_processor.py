import asyncio
import logging
from twilio.rest import Client
from config import settings
from api.twilio_routes import process_message, handle_onboarding
from database.models import UserConversation, ConversationArchive
from database.supabase import get_supabase_client
from database.redis_client import get_redis_client
from datetime import datetime, timezone
import json
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
twilio_number = settings.TWILIO_PHONE_NUMBER

# Get Redis client
redis_client = get_redis_client()

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
                    # Handle batched messages
                    msg = data['message']
                    if isinstance(msg, list):
                        msg_to_process = '\n'.join(msg)
                    else:
                        msg_to_process = msg
                    loop = asyncio.new_event_loop()
                    response = loop.run_until_complete(process_message(data['phone_number'], msg_to_process))
                    loop.close()
                    store_message(data['phone_number'], 'user', msg_to_process)
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
                msg = data['message']
                if isinstance(msg, list):
                    msg_to_process = '\n'.join(msg)
                else:
                    msg_to_process = msg
                loop = asyncio.new_event_loop()
                response = loop.run_until_complete(handle_onboarding(data['phone_number'], msg_to_process))
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


MAX_HISTORY = settings.MAX_HISTORY

def store_message(user_id, sender, content):
    supabase = get_supabase_client()
    now = datetime.now(timezone.utc)
    response = supabase.table('user_conversations').select('*').eq('user_id', user_id).order('started_at', desc=True).limit(1).execute()
    def store_one(msg):
        if response.data:
            convo = UserConversation(**response.data[0])
            convo.messages.append({
                "sender": sender,
                "content": msg,
                "timestamp": now.isoformat() + "Z"
            })
            convo.ended_at = now
            # If messages exceed MAX_HISTORY, archive the oldest
            if len(convo.messages) > MAX_HISTORY:
                to_archive = convo.messages[:-MAX_HISTORY]
                convo.messages = convo.messages[-MAX_HISTORY:]
                archive = ConversationArchive(
                    user_id=convo.user_id,
                    item_id=convo.item_id,
                    started_at=convo.started_at,
                    ended_at=now,
                    messages=to_archive
                )
                supabase.table('conversation_archives').insert(archive.dict()).execute()
            supabase.table('user_conversations').update(convo.dict()).eq('id', str(convo.id)).execute()
        else:
            messages = [{
                "sender": sender,
                "content": msg,
                "timestamp": now.isoformat() + "Z"
            }]
            new_convo = UserConversation(
                user_id=user_id,
                messages=messages,
                started_at=now,
                ended_at=now
            )
            supabase.table('user_conversations').insert(new_convo.dict()).execute()
    if isinstance(content, list):
        for msg in content:
            store_one(msg)
    else:
        store_one(content)