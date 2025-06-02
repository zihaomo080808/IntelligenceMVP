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
from onboarding.onboarding_messages import process_onboarding_message
from agents.conversation_agent import converse_with_user
import threading
import time

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

# Set up separate onboarding queue name
MESSAGING_QUEUE_NAME = 'twilio_messages'
ONBOARDING_QUEUE_NAME = 'onboarding_queue'

# Session window (in seconds)
SESSION_WINDOW = 3
# In-memory store for batching messages per user
user_message_batches = {}
user_timers = {}

# Helper to queue batched messages
def queue_batched_message(phone_number):
    batch = user_message_batches.pop(phone_number, [])
    if batch:
        message_data = {
            'phone_number': phone_number,
            'message': batch,  # List of strings
            'timestamp': str(time.time())
        }
        redis_client.lpush(MESSAGING_QUEUE_NAME, json.dumps(message_data))
        logger.info(f"Queued batched message for {phone_number}: {message_data['message']}")
    user_timers.pop(phone_number, None)

@twilio_bp.route("/webhook/sms", methods=['POST'])
def receive_sms():
    try:
        incoming_msg = request.values.get('Body', '').strip()
        sender = request.values.get('From', '')
        logger.info(f"Received message from {sender}: {incoming_msg}")
        resp = MessagingResponse()

        # Batch messages per user
        if sender not in user_message_batches:
            user_message_batches[sender] = []
        user_message_batches[sender].append(incoming_msg)

        # If a timer is already running, cancel it
        if sender in user_timers:
            user_timers[sender].cancel()
        # Start a new timer for this user
        timer = threading.Timer(SESSION_WINDOW, queue_batched_message, args=[sender])
        user_timers[sender] = timer
        timer.start()

        return str(resp)
    except Exception as e:
        logger.error(f"Error processing incoming SMS: {str(e)}")
        resp = MessagingResponse()
        resp.message("Sorry, we encountered an error processing your message.")
        return str(resp), 500

async def process_message(phone_number: str, message) -> str:
    try:
        # If message is a list, join with '\n'
        if isinstance(message, list):
            message_to_process = '\n'.join(message)
        else:
            message_to_process = message
        # Check if user has a profile in Supabase
        user_profile = await get_profile_by_phone(phone_number)
        if not user_profile:
            # Enqueue onboarding message instead of processing inline
            onboarding_message = {
                'phone_number': phone_number,
                'message': message,
                'timestamp': str(asyncio.get_event_loop().time())
            }
            redis_client.lpush(ONBOARDING_QUEUE_NAME, json.dumps(onboarding_message))
            return "Welcome! To get started, I'd like to know your name. What should I call you?"
        logger.info(f"Found profile for {phone_number}, processing with conversation agent")
        # Use converse_with_user to handle the message
        response = await converse_with_user(phone_number, message_to_process)
        if not response:
            logger.error(f"No response from conversation agent for {phone_number}")
            return "Hey! I'm having trouble processing that right now. Can you try again?"
        return response
    except Exception as e:
        logger.error(f"Error in process_message: {str(e)}")
        return "Sorry, I encountered an error. Please try again later."

async def handle_onboarding(phone_number: str, message) -> str:
    try:
        # If message is a list, join with '\n'
        if isinstance(message, list):
            message_to_process = '\n'.join(message)
        else:
            message_to_process = message
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
            message_to_process,
            user_state.step,
            phone_number,
            user_state.profile,
        )
        state_data = {
            'profile': updated_profile,
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