from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.analytics.audits import get_audits, get_stats
from app.api.depends.auth import UserDict, protected_first_party_app, require_auth
from app.pydantic.response import AnalyticsResponse
from app.utils.typed import FilterParams


class AnalyticsRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/analytics", tags=["analytics"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route("/audits", self.fetch_audits, methods=["GET"])
        self.router.add_api_route("/stats", self.fetch_stats, methods=["GET"])

    def _parse_query_params(self, request: Request) -> FilterParams:
        """
        Parses query parameters from the request
        and returns them as a QueryParams object.
        """
        user_id = request.query_params.get("user_id")
        page = int(request.query_params.get("page", 0))
        page_size = int(request.query_params.get("page_size", 25))
        search = request.query_params.get("search")
        audit_type = request.query_params.get("audit_type")
        results_status = request.query_params.get("status")

        return FilterParams(
            user_id=user_id,
            page=page,
            page_size=page_size,
            search=search,
            audit_type=audit_type,
            results_status=results_status,
        )

    async def fetch_audits(
        self,
        request: Request,
        user: UserDict = Depends(require_auth),
    ) -> AnalyticsResponse:
        # rate_limit(request=request, user=user)
        query = self._parse_query_params(request=request)

        response = await get_audits(
            user=user,
            query=query,
        )

        return JSONResponse(response.model_dump(), status_code=200)

    async def fetch_stats(
        self,
        request: Request,
    ) -> AnalyticsResponse:
        protected_first_party_app(request=request)

        response = await get_stats()

        return JSONResponse(response.model_dump(), status_code=200)
