# config.py
import os
from pathlib import Path
from pydantic_settings import BaseSettings
import logging

# Configure logging
logger = logging.getLogger(__name__)

# project root
BASE_DIR = Path(__file__).resolve().parent

# Log environment info
logger.warning("Config module loading...")

class Settings(BaseSettings):
    # base path for locating files in your repo
    BASE_DIR: Path = BASE_DIR

    OPENAI_API_KEY: str
    EMBEDDING_MODEL: str
    CLASSIFIER_MODEL: str
    GENERATOR_MODEL: str
    VECTOR_DIM: int
    VECTOR_INDEX_PATH: str
    DATABASE_URL: str

    # Perplexity API settings
    PERPLEXITY_API_KEY: str = os.getenv("PERPLEXITY_API_KEY", "")

    # Twilio settings
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # Redis settings
    REDIS_HOST: str = os.getenv('REDIS_HOST')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT'))
    REDIS_PASSWORD: str = os.getenv('REDIS_PASSWORD')
    REDIS_SSL: bool = os.getenv('REDIS_SSL', 'True').lower() == 'true'

    class Config:
        env_file = ".env"

settings = Settings()