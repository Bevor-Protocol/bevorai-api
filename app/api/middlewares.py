from datetime import datetime

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import redis_client
from app.prometheus import prom_logger
from app.utils.logger import request_url_var

endpoint_groupings = ["/ai", "/analytics", "/auth", "/blockchain", "/status"]


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        endpoint = request.url.path

        request_url_var.set(endpoint)

        group_use = None
        for grouping in endpoint_groupings:
            if endpoint.startswith(grouping):
                group_use = grouping
                break

        if not group_use:
            response = await call_next(request)
            return response

        prom_logger.api_active.inc()

        with prom_logger.api_duration.labels(method=method, endpoint=group_use).time():
            response = await call_next(request)

        prom_logger.api_requests.labels(
            method=method, endpoint=group_use, status_code=response.status_code
        ).inc()
        prom_logger.api_active.dec()

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.max_limit_per_minute = 30
        self.window_seconds = 60

    async def dispatch(self, request: Request, call_next):
        if request.url.path in [
            "/docs",
            "/openapi.json",
            "/",
            "/health",
            "/metrics",
            "/favicon.ico",
        ]:
            response = await call_next(request)
            return response
        if "webhook" in request.url.path:
            response = await call_next(request)
            return response

        bearer = request.headers.get("authorization")
        api_key = bearer.split(" ")[1]
        redis_key = f"rate_limit|{api_key}"

        current_time = int(datetime.now().timestamp())
        await redis_client.ltrim(redis_key, 0, self.max_limit_per_minute - 1)
        await redis_client.lrem(redis_key, 0, current_time - self.window_seconds)

        request_count = await redis_client.llen(redis_key)

        if request_count >= self.max_limit_per_minute:
            raise HTTPException(status_code=429, detail="Too many requests in a minute")

        await redis_client.rpush(redis_key, current_time)
        await redis_client.expire(redis_client, self.window_seconds)

        response = await call_next(request)
        return response
