import openai
from config import settings
from database.supabase import get_supabase_client
from agents.system_prompts import ALEX_HEFLE_PROMPT

async def converse_with_user(user_id: str, message: str) -> str:
    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    response = await client.chat.completions.create(
        model="o4-mini",
        messages=[
            {"role": "system", "content": ALEX_HEFLE_PROMPT},
            {"role": "user", "content": message}
        ],
    )
    return response.choices[0].message.content.strip()

# Example usage (for testing only):
# import asyncio
# print(asyncio.run(converse_with_user("+1234567890", "Hello!"))) 