from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.prometheus import logger


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        endpoint = request.url.path

        # useless to track this.
        if endpoint == "/metrics":
            response = await call_next(request)
            return response

        logger.api_active.inc()

        with logger.api_duration.labels(method=method, endpoint=endpoint).time():
            response = await call_next(request)

        logger.api_requests.labels(
            method=method, endpoint=endpoint, status_code=response.status_code
        ).inc()
        logger.api_active.dec()

        return response
