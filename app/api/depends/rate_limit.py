from datetime import datetime

from fastapi import HTTPException, Request

from app.api.middleware.auth import UserDict
from app.cache import redis_client
from app.utils.enums import AppTypeEnum

MAX_LIMIT_PER_MINUTE = 30
WINDOW_SECONDS = 60


async def rate_limit(request: Request, user: UserDict) -> None:
    if user["app"]:
        if user["app"].type == AppTypeEnum.FIRST_PARTY:
            return
    bearer = request.headers.get("authorization")
    api_key = bearer.split(" ")[1]
    redis_key = f"rate_limit|{api_key}"

    current_time = int(datetime.now().timestamp())
    redis_client.ltrim(redis_key, 0, MAX_LIMIT_PER_MINUTE)
    redis_client.lrem(redis_key, 0, current_time - WINDOW_SECONDS)

    request_count = redis_client.llen(redis_key)

    if request_count >= MAX_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Too many requests in a minute")

    redis_client.rpush(redis_key, current_time)
    redis_client.expire(redis_client, WINDOW_SECONDS)
