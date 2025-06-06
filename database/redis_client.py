import os
from redis import Redis
from config import settings
import logging

logger = logging.getLogger(__name__)

def get_redis_client():
    try:
        # For development, use localhost with default password
        host = 'localhost'
        port = 6379
        password = 'redis'  # Default Redis password
        logger.info(f"Using local Redis at {host}:{port}")
        
        redis_client = Redis(
            host=host,
            port=port,
            password=password,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        
        # Test the connection
        redis_client.ping()
        logger.info("Successfully connected to Redis")
        return redis_client
    except Exception as e:
        logger.error(f"Failed to initialize Redis client: {str(e)}")
        raise 