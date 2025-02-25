import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from tortoise.contrib.fastapi import register_tortoise

import app.api.routers as routers
from app.api.core.middlewares import PrometheusMiddleware
from app.config import TORTOISE_ORM
from app.utils.openapi import OPENAPI_SCHEMA

# from app.api.core.middlewares.auth import AuthenticationMiddleware
# from app.api.core.middlewares.rate_limit import RateLimitMiddleware

logging.basicConfig(level=logging.INFO)

load_dotenv()


app = FastAPI(debug=False, docs_url=None, redoc_url=None)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        **OPENAPI_SCHEMA["core"],
        routes=app.routes,
    )

    for k, v in OPENAPI_SCHEMA["other"].items():
        if isinstance(v, dict):
            openapi_schema.setdefault(k, {}).update(v)
        elif isinstance(v, list):
            openapi_schema.setdefault(k, []).extend(v)
        else:
            openapi_schema[k] = v
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


register_tortoise(
    app=app, config=TORTOISE_ORM, generate_schemas=False, add_exception_handlers=True
)


# # order matters. Runs in reverse order.
# app.add_middleware(RateLimitMiddleware)
# app.add_middleware(AuthenticationMiddleware)


app.add_middleware(PrometheusMiddleware)

app.include_router(routers.app_router)
app.include_router(routers.audit_router)
app.include_router(routers.auth_router)
app.include_router(routers.base_router)
app.include_router(routers.blockchain_router)
app.include_router(routers.contract_router)
app.include_router(routers.platform_router)
app.include_router(routers.user_router)
app.include_router(routers.static_router)
# app.include_router(routers.websocket_router) # exclude in favor of polling
