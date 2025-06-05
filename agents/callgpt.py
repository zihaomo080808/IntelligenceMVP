import asyncio
import openai
from asyncio_throttle import Throttler
from config import settings
import logging

logger = logging.getLogger(__name__)

gpt_throttler = Throttler(rate_limit=1000, period=1)
embedding_throttler = Throttler(rate_limit=1000, period=1)

async def call_gpt(messages, model="o4-mini", retries=3, **kwargs):
    for attempt in range(retries):
        try:
            async with gpt_throttler:
                client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    **kwargs
                )
                return response
        except openai.RateLimitError as e:
            logger.warning(f"OpenAI rate limit: {e}, attempt {attempt+1}")
            await asyncio.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"GPT call failed: {e}", exc_info=True)
            break
    return None

async def get_embedding(text: str, retries=3) -> list:
    for attempt in range(retries):
        try:
            async with embedding_throttler:
                client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                response = await client.embeddings.create(
                    model=settings.EMBEDDING_MODEL or "text-embedding-ada-002",
                    input=text
                )
                return response.data[0].embedding
        except openai.RateLimitError as e:
            logger.warning(f"OpenAI embedding rate limit: {e}, attempt {attempt+1}")
            await asyncio.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}", exc_info=True)
            break
    return None