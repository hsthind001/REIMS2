import redis
from app.core.config import settings

# Create Redis client
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)


# Dependency to get Redis client
def get_redis():
    return redis_client


# Helper functions for common Redis operations
def cache_set(key: str, value: str, expire: int = 3600):
    """Set a value in Redis with expiration time (default 1 hour)"""
    redis_client.setex(key, expire, value)


def cache_get(key: str):
    """Get a value from Redis"""
    return redis_client.get(key)


def cache_delete(key: str):
    """Delete a key from Redis"""
    redis_client.delete(key)

