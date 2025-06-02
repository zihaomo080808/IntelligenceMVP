import asyncio
from agents.conversation_agent import send_daily_recommendation
from database.supabase import get_supabase_client
from datetime import datetime, timezone
import pytz
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_all_user_profiles(batch_size=1000):
    supabase = get_supabase_client()
    offset = 0
    all_profiles = []
    while True:
        response = supabase.table('profiles').select('user_id, timezone').range(offset, offset + batch_size - 1).execute()
        batch = response.data if response.data else []
        if not batch:
            break
        all_profiles.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
    return all_profiles

def clear_recent_recommendations():
    supabase = get_supabase_client()
    response = supabase.table('recent_recommendations').select('user_id, recommendations').execute()
    if response.data:
        for row in response.data:
            user_id = row['user_id']
            recs = row.get('recommendations', [])
            if recs:
                # Clear recommendations for this user
                supabase.table('recent_recommendations').update({
                    'recommendations': []
                }).eq('user_id', user_id).execute()
                logger.info(f"Cleared recent recommendations for {user_id}")

async def main():
    clear_recent_recommendations()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=pytz.utc)
    user_profiles = get_all_user_profiles()
    for profile in user_profiles:
        user_id = profile['user_id']
        user_tz = profile.get('timezone')
        if not user_tz:
            logger.warning(f"No timezone for user {user_id}, skipping.")
            continue  # skip users without timezone info
        try:
            user_now = now_utc.astimezone(pytz.timezone(user_tz))
            if user_now.hour == 8:
                logger.info(f"Sending daily recommendation to {user_id} (timezone: {user_tz})")
                await send_daily_recommendation(user_id)
        except Exception as e:
            logger.error(f"Timezone error for user {user_id}: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 