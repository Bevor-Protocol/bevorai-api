import prometheus_client
from fastapi import APIRouter, Response
from tortoise import Tortoise


class BaseRouter:
    def __init__(self):
        self.router = APIRouter(tags=["job_status"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route("/", self.read_root, methods=["GET"])
        self.router.add_api_route("/health", self.health_check, methods=["GET"])
        self.router.add_api_route("/metrics", self.get_metrics, methods=["GET"])

    async def read_root(self):
        return {"Hello": "World"}

    async def health_check(self):
        try:
            await Tortoise.get_connection("default").execute_query("SELECT 1;")
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def get_metrics(self):
        return Response(
            content=prometheus_client.generate_latest(), media_type="text/plain"
        )
