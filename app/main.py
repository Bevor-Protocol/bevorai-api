import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
import logfire
from tortoise.contrib.fastapi import register_tortoise

from app.api.urls import router
from app.config import TORTOISE_ORM
from app.openapi import OPENAPI_SCHEMA

# from app.api.middlewares.auth import AuthenticationMiddleware
# from app.api.middlewares.rate_limit import RateLimitMiddleware

load_dotenv()
logfire.configure(
    environment=os.getenv("RAILWAY_ENVIRONMENT_NAME", "development"), service_name="api"
)


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

logfire.instrument_fastapi(app, excluded_urls=["/metrics"])

db_user = os.getenv("POSTGRES_USER")
db_pswd = os.getenv("POSTGRES_PASSWORD")
db_name = os.getenv("POSTGRES_DB")
db_host = os.getenv("PGHOST", "postgres:5432")
db_scheme = os.getenv("PGSCHEME", "postgresql")


register_tortoise(
    app=app,
    config=TORTOISE_ORM,
    generate_schemas=False,
    add_exception_handlers=True,
)

# # order matters. Runs in reverse order.
# app.add_middleware(RateLimitMiddleware)

app.include_router(router)
