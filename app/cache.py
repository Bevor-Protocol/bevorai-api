import os

from arq.connections import RedisSettings
from redis.asyncio import Redis

redis_settings = RedisSettings(host=os.getenv("REDIS_HOST"), port=6379)

redis_client = Redis(host=redis_settings.host, port=redis_settings.port)
