import os

from arq.connections import RedisSettings
from dotenv import load_dotenv
from redis.asyncio import Redis

redis_settings = RedisSettings(
    host=os.getenv("REDISHOST"),
    port=os.getenv("REDISPORT", 6379),
    username=os.getenv("REDISUSER"),
    password=os.getenv("REDISPASSWORD"),
)

redis_client = Redis(
    host=redis_settings.host,
    port=redis_settings.port,
    username=redis_settings.username,
    password=redis_settings.password,
)

load_dotenv()

db_user = os.getenv("POSTGRES_USER")
db_pswd = os.getenv("POSTGRES_PASSWORD")
db_name = os.getenv("POSTGRES_DB")
db_host = os.getenv("PGHOST", "postgres:5432")
db_scheme = os.getenv("PGSCHEME", "postgresql")

TORTOISE_ORM = {
    "connections": {
        "default": f"{db_scheme}://{db_user}:{db_pswd}@{db_host}/{db_name}"
    },
    "apps": {
        "models": {
            "models": ["app.db.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
