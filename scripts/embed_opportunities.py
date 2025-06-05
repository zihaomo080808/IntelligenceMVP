import asyncio
import logging
import os
import sys
from typing import List, Dict, Any

# Add the project root directory to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from openai import AsyncOpenAI
from config import settings
from database.supabase import get_supabase_client
from database.models import Opportunity

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def get_opportunities() -> List[Dict[str, Any]]:
    """Fetch all opportunities from Supabase that don't have embeddings."""
    try:
        supabase = get_supabase_client()
        response = supabase.table('opportunities').select('*').is_('embedding', 'null').execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching opportunities: {str(e)}")
        return []

async def generate_embedding(text: str) -> List[float]:
    """Generate embedding for the given text using OpenAI's API."""
    try:
        response = await client.embeddings.create(
            input=text,
            model=settings.EMBEDDING_MODEL
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        return None

async def update_opportunity_embedding(opportunity_id: str, embedding: List[float]):
    """Update the opportunity with its embedding in Supabase."""
    try:
        supabase = get_supabase_client()
        response = supabase.table('opportunities').update({
            'embedding': embedding
        }).eq('id', opportunity_id).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error updating opportunity embedding: {str(e)}")
        return None

async def process_opportunity(opportunity: Dict[str, Any]):
    """Process a single opportunity to generate and store its embedding."""
    try:
        # Combine relevant fields for embedding
        text_to_embed = f"{opportunity.get('title', '')} {opportunity.get('description', '')} {opportunity.get('type', '')} {opportunity.get('state', '')} {opportunity.get('city', '')}"
        
        # Generate embedding
        embedding = await generate_embedding(text_to_embed)
        if embedding:
            # Update opportunity with embedding
            await update_opportunity_embedding(opportunity['id'], embedding)
            logger.info(f"Successfully embedded opportunity: {opportunity['id']}")
        else:
            logger.error(f"Failed to generate embedding for opportunity: {opportunity['id']}")
    except Exception as e:
        logger.error(f"Error processing opportunity {opportunity.get('id')}: {str(e)}")

async def main():
    """Main function to process all opportunities."""
    try:
        # Get all opportunities without embeddings
        opportunities = await get_opportunities()
        logger.info(f"Found {len(opportunities)} opportunities to process")
        
        # Process each opportunity
        for opportunity in opportunities:
            await process_opportunity(opportunity)
            
        logger.info("Finished processing all opportunities")
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 