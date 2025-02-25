from typing import Annotated

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from tortoise.exceptions import DoesNotExist

from app.api.core.dependencies import Authentication, RequireCredits
from app.api.services.ai import AiService
from app.api.services.audit import AuditService
from app.utils.openapi import OPENAPI_SPEC
from app.utils.schema.request import EvalBody, FeedbackBody, FilterParams
from app.utils.schema.response import GetAuditStatusResponse
from app.utils.schema.shared import BooleanResponse
from app.utils.types.enums import AuthRequestScopeEnum


class AuditRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/audit", tags=["audit"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "",
            self.create_audit,
            methods=["POST"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER)),
                Depends(RequireCredits()),
            ],
            **OPENAPI_SPEC["create_audit"],
        )
        self.router.add_api_route(
            "/list",
            self.list_audits,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
            **OPENAPI_SPEC["get_audits"],
        )
        self.router.add_api_route(
            "/{id}",
            self.get_audit,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
            **OPENAPI_SPEC["get_audit"],
        )
        self.router.add_api_route(
            "/{id}/status",
            self.get_audit_status,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
            **OPENAPI_SPEC["get_audit_status"],
        )
        self.router.add_api_route(
            "/{id}/feedback",
            self.submit_feedback,
            methods=["POST"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
            **OPENAPI_SPEC["submit_feedback"],
        )

    async def create_audit(
        self,
        request: Request,
        body: Annotated[EvalBody, Body()],
    ):
        ai_service = AiService()
        response = await ai_service.process_evaluation(
            auth=request.state.auth, data=body
        )
        return Response(response.model_dump_json(), status_code=status.HTTP_201_CREATED)

    async def list_audits(
        self,
        request: Request,
        query_params: Annotated[FilterParams, Query()],
    ):
        # rate_limit(request=request, user=user)
        audit_service = AuditService()
        response = await audit_service.get_audits(
            auth=request.state.auth,
            query=query_params,
        )

        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)

    async def get_audit(self, request: Request, id: str):
        audit_service = AuditService()

        try:
            audit = await audit_service.get_audit(auth=request.state.auth, id=id)
            return Response(audit.model_dump_json(), status_code=status.HTTP_200_OK)
        except DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="this audit does not exist under these credentials",
            )

    async def get_audit_status(
        self, request: Request, id: str
    ) -> GetAuditStatusResponse:
        audit_service = AuditService()

        try:
            response = await audit_service.get_status(auth=request.state.auth, id=id)
            return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)
        except DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="this audit does not exist under these credentials",
            )

    async def submit_feedback(self, request: Request, data: FeedbackBody, id: str):
        audit_service = AuditService()
        response = await audit_service.submit_feedback(
            data=data, auth=request.state.auth, id=id
        )
        return Response(
            BooleanResponse(success=response).model_dump_json(),
            status_code=status.HTTP_201_CREATED,
        )
