import asyncio
import logging
from twilio.rest import Client
from config import settings
from twilio_routes import process_message
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
twilio_number = settings.TWILIO_PHONE_NUMBER

redis_client = settings.redis_client

def process_queued_messages():
    """
    This function should be run in a separate process continuously.
    """
    logger.info("Starting message processor...")
    while True:
        try:
            # Get the oldest message from the queue
            message_data = redis_client.rpop('twilio_messages')
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

if __name__ == "__main__":
    process_queued_messages() 