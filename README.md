# Intelligence Layer

A project that combines Twilio SMS, Supabase, and AI to create an intelligent conversational system with user profiles.

## Project Structure

The project is organized as follows:

- `agents/` - Conversation agents
- `api/` - API routes and endpoints
  - `twilio_routes.py` - Handles Twilio SMS integration
- `classifier/` - Model for classifying content
- `config.py` - Configuration settings
- `database/` - Database models and utilities
  - `models.py` - Pydantic models for data
  - `supabase.py` - Supabase client utilities
  - `phone_mapping.py` - Utilities for mapping phone numbers to user IDs
  - `supabase_schema.sql` - SQL schema for Supabase setup
- `feedback/` - Feedback processing
- `generator/` - Content generation
- `matcher/` - Profile matching
- `onboarding/` - User onboarding
  - `onboarding_messages.py` - Original onboarding logic
  - `onboarding_supabase.py` - Supabase-integrated onboarding
- `profiles/` - User profile management
  - `profiles.py` - Supabase profile CRUD operations

## Setup

### 1. Environment Variables

Create a `.env` file with the following variables:

```
OPENAI_API_KEY=your_openai_api_key
EMBEDDING_MODEL=text-embedding-ada-002
CLASSIFIER_MODEL=gpt-3.5-turbo
GENERATOR_MODEL=gpt-3.5-turbo
VECTOR_DIM=1536
VECTOR_INDEX_PATH=./vectorstore
DATABASE_URL=your_database_url

PERPLEXITY_API_KEY=your_perplexity_api_key

TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number
DEBUG=False

SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

### 2. Supabase Setup

1. Create a new Supabase project
2. Run the SQL in `database/supabase_schema.sql` to set up the necessary tables
3. Enable phone authentication in Supabase Auth settings if you plan to use it

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
flask run
```

Or if using FastAPI:

```bash
uvicorn api.main:app --reload
```

## User Onboarding Flow

1. User sends a message to the Twilio number
2. System checks if the user has a profile in Supabase
3. If no profile exists, system starts onboarding:
   - Step 0: Asks for the user's name
   - Step 1: Asks for background info (location, education, occupation)
   - Step 2: Asks for interests and opportunities
4. System creates a profile in Supabase with the extracted information
5. System creates a mapping between the user's phone number and user ID

## API Endpoints

### Twilio Endpoints

- `POST /webhook/sms` - Receives incoming SMS messages
- `POST /send/sms` - Sends outgoing SMS messages (requires `to` and `message` fields)

## Database Schema

### Profiles Table

```sql
CREATE TABLE public.profiles (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  username     TEXT NOT NULL UNIQUE,
  location     TEXT,
  bio          TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Phone Users Table

```sql
CREATE TABLE public.phone_users (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone        TEXT NOT NULL UNIQUE,
  user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```