from datetime import datetime

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.cache import redis_client


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.max_limit_per_minute = 30
        self.window_seconds = 60

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/docs", "/openapi.json", "/", "/health"]:
            response = await call_next(request)
            return response
        if "webhook" in request.url.path:
            response = await call_next(request)
            return response
        if not request.state.require_credit_and_limit:
            response = await call_next(request)
            return response

        bearer = request.headers.get("authorization")
        api_key = bearer.split(" ")[1]
        redis_key = f"rate_limit|{api_key}"

        current_time = int(datetime.now().timestamp())
        redis_client.ltrim(redis_key, 0, self.max_limit_per_minute - 1)
        redis_client.lrem(redis_key, 0, current_time - self.window_seconds)

        request_count = redis_client.llen(redis_key)

        if request_count >= self.max_limit_per_minute:
            raise HTTPException(status_code=429, detail="Too many requests in a minute")

        redis_client.rpush(redis_key, current_time)
        redis_client.expire(redis_client, self.window_seconds)

        response = await call_next(request)
        return response
