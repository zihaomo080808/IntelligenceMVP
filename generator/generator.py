# generator/generator.py
from openai import OpenAI
import logging
import os
from config import settings
from .cot_prompt import build_prompt
import random

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
# Add debugging information
logger.info(f"OPENAI_API_KEY length: {len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0}")
logger.info(f"GENERATOR_MODEL: {settings.GENERATOR_MODEL}")
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def generate_recommendation(profile, items):
    msgs = build_prompt(profile, items)
    try:
        logger.info(f"Calling OpenAI API for text generation with model: {settings.GENERATOR_MODEL}")
        logger.info(f"Messages being sent (first prompt): {msgs[0]['content'] if msgs else 'No messages'}")

        try:
            # Minimal parameters for compatibility with o4-mini model
            resp = client.chat.completions.create(
                model=settings.GENERATOR_MODEL,
                messages=msgs
            )

            if not resp or not resp.choices or len(resp.choices) == 0:
                logger.error("Empty response from OpenAI API")
                raise ValueError("Empty response from OpenAI API")

            content = resp.choices[0].message.content
            logger.info(f"OpenAI API Response (first 100 chars): {content[:100] if content else 'Empty response'}...")

            if not content or len(content.strip()) < 10:
                raise ValueError("Response content too short or empty")

            return content

        except Exception as api_error:
            logger.error(f"API Error: {str(api_error)}")
            raise api_error
            
    except Exception as e:
        logger.error(f"Error generating recommendation: {str(e)}")