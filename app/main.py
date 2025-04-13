import os

import logfire
from dotenv import load_dotenv
from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise

from app.api.urls import router
from app.config import TORTOISE_ORM

from .openapi import customize_openapi

load_dotenv()
logfire.configure(
    environment=os.getenv("RAILWAY_ENVIRONMENT_NAME", "development"), service_name="api"
)


app = FastAPI(debug=False, docs_url=None, redoc_url=None)


app.openapi = customize_openapi(app)

logfire.instrument_fastapi(app, excluded_urls=["/metrics"])

register_tortoise(
    app=app,
    config=TORTOISE_ORM,
    generate_schemas=False,
    add_exception_handlers=True,
)

# # order matters. Runs in reverse order.
# app.add_middleware(RateLimitMiddleware)

app.include_router(router)
