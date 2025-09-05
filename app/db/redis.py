import redis.asyncio as redis
from app.core.config import settings

r = redis.from_url(settings.REDIS_URL, decode_responses=True)
