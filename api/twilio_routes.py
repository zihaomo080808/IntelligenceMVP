from flask import Blueprint, request, jsonify
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import logging
import asyncio
import json
from redis import Redis
from config import settings
from database.supabase import get_supabase_client
from profiles.profiles import get_profile_by_phone, get_user_profile, get_user_state, create_user_state, update_user_state, delete_user_state
from onboarding.onboarding_messages import process_onboarding_message, extract_name_from_greeting

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

twilio_bp = Blueprint('twilio', __name__)

# Initialize Twilio client
client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
twilio_number = settings.TWILIO_PHONE_NUMBER

# Initialize Redis connection
redis_client = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    ssl=settings.REDIS_SSL,
    decode_responses=True  # This ensures we get strings back instead of bytes
)

# Export redis_client to settings for use in message_processor.py
settings.redis_client = redis_client

@twilio_bp.route("/webhook/sms", methods=['POST'])
def receive_sms():
    try:
        # Get the message the user sent
        incoming_msg = request.values.get('Body', '').strip()
        sender = request.values.get('From', '')
        
        logger.info(f"Received message from {sender}: {incoming_msg}")
        
        # Create a TwiML response
        resp = MessagingResponse()
        
        # Queue the message in Redis
        message_data = {
            'phone_number': sender,
            'message': incoming_msg,
            'timestamp': str(asyncio.get_event_loop().time())
        }
        redis_client.lpush('twilio_messages', json.dumps(message_data))
        return str(resp)
    except Exception as e:
        logger.error(f"Error processing incoming SMS: {str(e)}")
        resp = MessagingResponse()
        resp.message("Sorry, we encountered an error processing your message.")
        return str(resp), 500

async def process_message(phone_number: str, message: str) -> str:
    try:
        # Check if user has a profile in Supabase
        user_profile = await get_profile_by_phone(phone_number)
        if not user_profile:
            return await handle_onboarding(phone_number, message)
        
        logger.info(f"Found profile for {phone_number}, handling as regular conversation")
        # For now, just acknowledge the message - you'd replace this with your conversation agent
        return f"Hello {user_profile.username}! Thank you for your message. How can I help you today?"
    except Exception as e:
        logger.error(f"Error in process_message: {str(e)}")
        return "Sorry, I encountered an error. Please try again later."

async def handle_onboarding(phone_number: str, message: str) -> str:
    try:
        # Get or create user state
        user_state = await get_user_state(phone_number)
        if not user_state:
            # Create new state with initial step 0
            user_state = await create_user_state(
                phone_number=phone_number,
                step=0,
                profile={"user_id": phone_number},  # Initialize with at least the user_id
                accumulated_messages=[]  # Empty list will be stored as JSONB array
            )
            if not user_state:
                return "Sorry, I encountered an error, trace to profiles.profiles.py function create_user_state."
            
            return "Welcome! To get started, I'd like to know your name. What should I call you?"
        # Process the message based on the current onboarding step
        updated_profile, next_question, is_complete = await process_onboarding_message(
            message,
            user_state.step,
            phone_number,
            user_state.profile,
            user_state.accumulated_messages
        )
        
        state_data = {
            'profile': updated_profile,
            'accumulated_messages': user_state.accumulated_messages + [message]
        }
        
        if is_complete:
            await delete_user_state(phone_number)
            return next_question
        else:
            state_data['step'] = user_state.step + 1
            await update_user_state(phone_number, state_data)
            return next_question
            
    except Exception as e:
        logger.error(f"Error in handle_onboarding: {str(e)}")
        return "Error in handle_onboarding function"

@twilio_bp.route("/send/sms", methods=['POST'])
def send_sms():
    try:
        data = request.get_json()
        
        if not data or 'to' not in data or 'message' not in data:
            return jsonify({'error': 'Missing required fields: to and message'}), 400
            
        to_number = data['to']
        message_body = data['message']
        
        # Queue the message in Redis
        message_data = {
            'phone_number': to_number,
            'message': message_body,
            'timestamp': str(asyncio.get_event_loop().time()),
            'is_outbound': True  
        }
        redis_client.lpush('twilio_messages', json.dumps(message_data))
        
        logger.info(f"Queued message to {to_number}, twilio_routes.py line 134")
        
        return jsonify({
            'success': True,
            'message': 'Message queued for delivery'
        })
        
    except Exception as e:
        logger.error(f"Error queueing SMS: {str(e)}")
        return jsonify({'error': str(e)}), 500