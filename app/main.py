from dotenv import load_dotenv
from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise

import app.api.routers as routers
from app.db.config import TORTOISE_ORM

# from app.api.middleware.auth import AuthenticationMiddleware
# from app.api.middleware.rate_limit import RateLimitMiddleware


load_dotenv()


app = FastAPI(debug=False)


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
app.include_router(routers.analytics_router)
