from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.prometheus import logger

endpoint_groupings = ["/ai", "/analytics", "/auth", "/blockchain", "/status"]


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        endpoint = request.url.path

        group_use = None
        for grouping in endpoint_groupings:
            if endpoint.startswith(grouping):
                group_use = grouping
                break

        if not group_use:
            response = await call_next(request)
            return response

        logger.api_active.inc()

        with logger.api_duration.labels(method=method, endpoint=group_use).time():
            response = await call_next(request)

        logger.api_requests.labels(
            method=method, endpoint=group_use, status_code=response.status_code
        ).inc()
        logger.api_active.dec()

        return response
