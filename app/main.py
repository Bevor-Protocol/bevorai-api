import logging
from contextlib import asynccontextmanager

from aerich import Command
from dotenv import load_dotenv
from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise

import app.api.routers as routers
from app.api.middleware.auth import AuthenticationMiddleware
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.db.config import TORTOISE_ORM

from .jobs import scheduler

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Running Migrations...")
    aerich_command = Command(
        tortoise_config=TORTOISE_ORM, location="./app/db/migrations"
    )
    await aerich_command.init()
    migrations = await aerich_command.upgrade()
    if migrations:
        str_migrations = "\n".join(migrations)
        logging.info(f"Ran the following migrations:\n{str_migrations}")
    else:
        logging.info("No migrations detected")

    scheduler.start()
    yield
    print("shutting down")
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

register_tortoise(
    app=app, config=TORTOISE_ORM, generate_schemas=False, add_exception_handlers=True
)

# order matters. Runs in reverse order.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthenticationMiddleware)

app.include_router(routers.health_router)
app.include_router(routers.blockchain_router)
app.include_router(routers.ai_router)
app.include_router(routers.status_router)
app.include_router(routers.websocket_router)
app.include_router(routers.auth_router)
