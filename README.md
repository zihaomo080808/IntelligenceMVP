# Intelligence MVP - Twilio Integration

This project implements a Twilio-based SMS messaging system with conversation handling and user onboarding capabilities.

## Prerequisites

- Python 3.8 or higher
- Redis server
- Supabase account
- Twilio account
- OpenAI API key
- Perplexity API key (optional)

## Environment Setup

1. Create a `.env` file in the root directory with the following variables:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
EMBEDDING_MODEL=your_embedding_model
CLASSIFIER_MODEL=your_classifier_model
GENERATOR_MODEL=your_generator_model
VECTOR_DIM=your_vector_dimension
VECTOR_INDEX_PATH=your_vector_index_path

# Twilio Configuration
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# Redis Configuration
REDIS_HOST=your_redis_host
REDIS_PORT=your_redis_port
REDIS_PASSWORD=your_redis_password
REDIS_SSL=True

# Optional Configuration
PERPLEXITY_API_KEY=your_perplexity_api_key
DEBUG=False
```

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the Redis server:
```bash
redis-server
```

2. Start the Flask application:
```bash
python app.py
```

## Twilio Setup

1. Log in to your Twilio account
2. Configure your Twilio phone number's webhook:
   - Set the webhook URL to: `https://your-domain.com/webhook/sms`
   - Set the HTTP method to POST

## Features

- SMS message handling with Twilio
- User onboarding flow
- Conversation management
- Message batching
- Redis-based message queuing
- Supabase database integration

## API Endpoints

- `/webhook/sms` (POST): Receives incoming SMS messages
- `/send/sms` (POST): Sends SMS messages
  - Required JSON body:
    ```json
    {
        "to": "recipient_phone_number",
        "message": "message_content"
    }
    ```

## Message Processing

The system processes messages in the following way:
1. Incoming messages are received through the Twilio webhook
2. Messages are batched per user with a 3-second window
3. Messages are queued in Redis for processing
4. The system checks if the user is onboarded
5. If not onboarded, the user goes through the onboarding flow
6. If onboarded, messages are processed by the conversation agent

## Error Handling

The system includes comprehensive error handling and logging. All errors are logged and appropriate error messages are sent back to users when necessary.

## Security Notes

- Never commit your `.env` file
- Keep your API keys and tokens secure
- Use HTTPS for your webhook endpoints
- Regularly rotate your API keys and tokens

## Support

For any issues or questions, please open an issue in the repository.
