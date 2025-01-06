from fastapi import APIRouter
from tortoise import Tortoise


class HealthRouter:
    def __init__(self):
        self.router = APIRouter(tags=["job_status"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route("/", self.read_root, methods=["GET"])
        self.router.add_api_route("/health", self.health_check, methods=["GET"])

    async def read_root(self):

        return {"Hello": "World"}

    async def health_check(self):
        try:
            await Tortoise.get_connection("default").execute_query("SELECT 1;")
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
