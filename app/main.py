from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise

import app.api.routers as routers

# from app.api.middleware.auth import AuthenticationMiddleware
# from app.api.middleware.rate_limit import RateLimitMiddleware
from app.db.config import TORTOISE_ORM

from .cron import scheduler

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    print("shutting down")
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan, debug=False)


register_tortoise(
    app=app, config=TORTOISE_ORM, generate_schemas=False, add_exception_handlers=True
)

# # order matters. Runs in reverse order.
# app.add_middleware(RateLimitMiddleware)
# app.add_middleware(AuthenticationMiddleware)

app.include_router(routers.base_router)
app.include_router(routers.blockchain_router)
app.include_router(routers.ai_router)
app.include_router(routers.status_router)
app.include_router(routers.websocket_router)
app.include_router(routers.auth_router)
