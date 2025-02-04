from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.api.analytics.audits import get_audit, get_audits, get_stats, submit_feeback
from app.api.analytics.user import get_user_info
from app.api.depends.auth import protected_first_party_app, require_auth
from app.pydantic.request import FeedbackBody
from app.pydantic.response import AnalyticsResponse
from app.utils.typed import FilterParams


def _parse_query_params(request: Request) -> FilterParams:
    """
    Parses query parameters from the request
    and returns them as a QueryParams object.
    """
    query = FilterParams()

    for k, v in query.model_dump().items():
        value = request.query_params.get(k)
        if not value:
            continue
        if isinstance(v, list):
            setattr(query, k, value.split(","))
        elif isinstance(v, int):
            setattr(query, k, int(value))
        elif isinstance(v, str):
            setattr(query, k, value)
        # Add more type checks as necessary for other types
        else:
            setattr(query, k, value)

    return query


class AnalyticsRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/analytics", tags=["analytics"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "/audits",
            self.fetch_audits,
            methods=["GET"],
            dependencies=[Depends(require_auth)],
        )
        self.router.add_api_route("/stats", self.fetch_stats, methods=["GET"])
        self.router.add_api_route("/audit/{id}", self.get_audit, methods=["GET"])
        self.router.add_api_route(
            "/feedback",
            self.submit_feedback,
            methods=["POST"],
            dependencies=[Depends(require_auth)],
        )
        self.router.add_api_route(
            "/user",
            self.get_user_info,
            methods=["GET"],
            dependencies=[Depends(require_auth)],
        )

    async def fetch_audits(
        self,
        request: Request,
        query_params: FilterParams = Query(_parse_query_params),
    ) -> AnalyticsResponse:
        # rate_limit(request=request, user=user)
        response = await get_audits(
            user=request.scope["auth"],
            query=query_params,
        )

        return JSONResponse(response.model_dump(), status_code=200)

    async def fetch_stats(
        self,
        request: Request,
    ) -> AnalyticsResponse:
        await protected_first_party_app(request=request)

        response = await get_stats()

        return JSONResponse(response.model_dump(), status_code=200)

    async def get_audit(self, id: str):
        audit = await get_audit(id)
        return JSONResponse({"result": audit}, status_code=200)

    async def get_user_info(self, request: Request):
        user_info = await get_user_info(request.scope["auth"])
        return JSONResponse(user_info.model_dump(), status_code=200)

    async def submit_feedback(self, request: Request, data: FeedbackBody):
        response = await submit_feeback(data=data, user=request.scope["auth"])
        return JSONResponse({"success": response}, status_code=200)
