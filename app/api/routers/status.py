from fastapi import APIRouter

from app.api.status.worker import fetch_job_status, retry_failed_job


class StatusRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/status", tags=["job_status"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route("/job/{job_id}", self.get_job_status, methods=["GET"])
        self.router.add_api_route(
            "/job/retry/{job_id}", self.get_failed_jobs, methods=["POST"]
        )

    def get_job_status(self, job_id: str):
        response = fetch_job_status(job_id)
        return response

    def get_failed_jobs(self, job_id: str):
        return retry_failed_job(job_id)
