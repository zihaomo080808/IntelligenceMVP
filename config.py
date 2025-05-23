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
    PERPLEXITY_API_KEY: str = ""

    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    REDIS_HOST: str = ""
    REDIS_PORT: int = int(os.getenv('REDIS_PORT'))
    REDIS_PASSWORD: str = ""
    REDIS_SSL: bool = os.getenv('REDIS_SSL', 'True').lower() == 'true'
    MAX_HISTORY: int = 50

    class Config:
        env_file = ".env"

settings = Settings()