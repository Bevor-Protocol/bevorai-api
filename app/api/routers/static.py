from typing import Annotated

from fastapi import (
    APIRouter,
    Body,
    Depends,
    Request,
    Response,
    status,
)
from fastapi.responses import JSONResponse

from app.api.core.dependencies import Authentication
from app.api.services.ai import AiService
from app.schema.request import EvalBody
from app.utils.enums import AuthRequestScopeEnum
from app.utils.openapi import OPENAPI_SPEC


class StaticRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/static", tags=["static"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "/token",
            self.process_token,
            methods=["POST"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
            **OPENAPI_SPEC["analyze_token"],
        )

    async def process_token(
        self,
        request: Request,
        body: Annotated[EvalBody, Body()],
    ):
        sa_service = StaticAnalysisService()
        response = await sa_service.process_static_eval_token(
            auth=request.state.auth, data=body
        )

        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)
