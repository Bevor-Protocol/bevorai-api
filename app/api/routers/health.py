from arq import create_pool
from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from tortoise import Tortoise

from app.cache import redis_settings
from app.prometheus import logger


class BaseRouter:
    def __init__(self):
        self.router = APIRouter(tags=["job_status"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route("/", self.read_root, methods=["GET"])
        self.router.add_api_route("/health", self.health_check, methods=["GET"])
        self.router.add_api_route("/metrics", self.get_metrics, methods=["GET"])
        self.router.add_api_route("/enqueue", self.enqueue, methods=["GET"])

    async def read_root(self):
        with logger.active_requests.track_inprogress():
            logger.http_requests.labels(method="GET", endpoint="/").inc()
            return {"Hello": "World"}

    async def health_check(self):
        with logger.active_requests.track_inprogress():
            logger.http_requests.labels(method="GET", endpoint="/health").inc()
            try:
                await Tortoise.get_connection("default").execute_query("SELECT 1;")
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}

    async def enqueue(self):
        redis_pool = await create_pool(redis_settings)
        job = await redis_pool.enqueue_job("mock")
        return JSONResponse({"ok": True, "job": job.job_id})

    async def get_metrics(self):
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
