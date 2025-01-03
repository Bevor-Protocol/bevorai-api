import hashlib
import hmac
import os
from datetime import datetime

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/docs", "/openapi.json"]:
            return await call_next(request)

        secret = os.getenv("SHARED_SECRET")

        signature = request.headers.get("X-Signature")
        timestamp = request.headers.get("X-Timestamp")

        if signature and timestamp:
            current_time = int(datetime.now().timestamp() * 1000)
            timestamp_int = int(timestamp)
            if abs(current_time - timestamp_int) > 3000:
                raise HTTPException(status_code=401, detail="Request timestamp expired")
            payload = f"{timestamp}:{request.url.path}"
            expected_signature = hmac.new(
                secret.encode(), payload.encode(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected_signature):
                raise HTTPException(status_code=401, detail="Invalid signature")

            request.state.user = "certaik"

        response = await call_next(request)
        return response
