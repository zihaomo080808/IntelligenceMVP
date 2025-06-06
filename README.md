# IntelligenceLayerFinal

A scalable, async, multi-channel conversational AI backend with OpenAI integration, SMS (Twilio) support, onboarding, persistent conversation history, and opportunity recommendation tracking.

## Features

- **OpenAI GPT Integration**: Async, rate-limited calls to OpenAI's GPT and embedding APIs.
- **Twilio SMS Support**: Receive and send SMS via Twilio, with message batching and queueing.
- **Onboarding Flow**: New users are onboarded with a stepwise profile creation process.
- **Persistent Conversation History**: User conversations are stored and archived in a database (Supabase).
- **Async Processing**: Uses Redis-backed queues and background threads for scalable message processing.
- **Opportunity Recommendations**: Recommends opportunities to users via the OpenAI Search API and tracks what has already been recommended to avoid duplicates.
- **Configurable via Environment Variables**.

## Directory Structure

- `app.py` — Main Flask app entry point.
- `agents/` — GPT and conversation agent logic.
- `api/` — API endpoints and message processing.
- `database/` — Database models and Supabase integration.
- `onboarding/` — Onboarding message logic.
- `profiles/` — User profile management.
- `feedback/` — Feedback and enhanced Rocchio logic.
- `config.py` — Centralized configuration.

## Installation

1. **Clone the repository**  
   ```bash
   git clone <repo-url>
   cd intelligencelayerfinal
   ```

2. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**  
   Create a `.env` file in the root directory with the following (see `config.py` for all options):

   ```
   OPENAI_API_KEY=your_openai_key
   EMBEDDING_MODEL=text-embedding-ada-002
   CLASSIFIER_MODEL=...
   GENERATOR_MODEL=...
   VECTOR_DIM=...
   VECTOR_INDEX_PATH=...
   DATABASE_URL=...
   PERPLEXITY_API_KEY=...
   TWILIO_ACCOUNT_SID=...
   TWILIO_AUTH_TOKEN=...
   TWILIO_PHONE_NUMBER=...
   SUPABASE_URL=...
   SUPABASE_SERVICE_ROLE_KEY=...
   REDIS_HOST=...
   REDIS_PORT=6379
   REDIS_PASSWORD=...
   REDIS_SSL=True
   MAX_HISTORY=50
   ```

## Usage

### Development

```bash
python app.py
```

- The Flask app will start on `http://0.0.0.0:5000`.
- Message processing runs in a background thread.

### Production

Use a WSGI server like Gunicorn (see `Procfile` for an example):

```bash
gunicorn app:app
```

## API Endpoints

- `POST /twilio/webhook/sms` — Receive incoming SMS (Twilio webhook).
- `POST /twilio/send/sms` — Queue an outbound SMS for delivery.

## Opportunity Recommendation Tracking

To avoid recommending the same opportunity to a user more than once, the system stores each recommendation in a `user_recommendations` table in the database (Supabase/Postgres). Each record includes:

- `user_id`: The identifier for the user (e.g., phone number).
- `opportunity_id`: The unique ID of the opportunity.
- `recommended_at`: Timestamp of when the recommendation was made.

**Workflow:**
1. Before recommending, the system queries this table to see what has already been recommended to the user.
2. It filters out previously recommended opportunities from the OpenAI Search API results.
3. After sending new recommendations, it inserts a record for each into the table.

**Example Table Schema:**
```sql
CREATE TABLE user_recommendations (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    opportunity_id TEXT NOT NULL,
    recommended_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

## Customization

- **Rate Limits**: Adjust in `agents/callgpt.py` via the `Throttler` parameters.
- **Onboarding**: Customize onboarding steps in `onboarding/onboarding_messages.py`.
- **Conversation Logic**: Extend or modify in `agents/conversation_agent.py`.

## Dependencies

See `requirements.txt` for the full list, including:
- Flask, FastAPI, Uvicorn
- OpenAI, Twilio, Supabase
- Redis, SQLAlchemy, Pydantic, etc.

## License

MIT 