from typing import Annotated

import logfire
from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from tortoise.exceptions import DoesNotExist

from app.api.dependencies import Authentication, RequireCredits
from app.lib.clients.agent import worker as game_worker
from app.utils.openapi_tags import AUDIT_TAG
from app.utils.types.enums import RoleEnum
from app.utils.types.shared import BooleanResponse

from .interface import (
    AuditResponse,
    AuditsResponse,
    CreateEvalResponse,
    EvalBody,
    FeedbackBody,
    FilterParams,
    GetAuditStatusResponse,
)
from .openapi import (
    CREATE_AUDIT,
    GET_AUDIT,
    GET_AUDIT_STATUS,
    GET_AUDITS,
    SUBMIT_FEEDBACK,
)
from .service import AuditService


class AuditRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/audit", tags=[AUDIT_TAG])

        self.add_api_route(
            "",
            self.create_audit,
            methods=["POST"],
            dependencies=[
                Depends(Authentication(required_role=RoleEnum.USER)),
                Depends(RequireCredits()),
            ],
            status_code=status.HTTP_201_CREATED,
            **CREATE_AUDIT,
        )
        self.add_api_route(
            "/list",
            self.list_audits,
            methods=["GET"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
            status_code=status.HTTP_200_OK,
            **GET_AUDITS,
        )
        self.add_api_route(
            "/{id}",
            self.get_audit,
            methods=["GET"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
            status_code=status.HTTP_200_OK,
            **GET_AUDIT,
        )
        self.add_api_route(
            "/{id}/status",
            self.get_audit_status,
            methods=["GET"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
            status_code=status.HTTP_200_OK,
            **GET_AUDIT_STATUS,
        )
        self.add_api_route(
            "/{id}/feedback",
            self.submit_feedback,
            methods=["POST"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
            status_code=status.HTTP_201_CREATED,
            **SUBMIT_FEEDBACK,
        )
        self.add_api_route(
            "/game", self.game, methods=["POST"], include_in_schema=False
        )

    async def create_audit(
        self,
        request: Request,
        body: Annotated[EvalBody, Body()],
    ) -> CreateEvalResponse:
        audit_service = AuditService()
        audit = await audit_service.initiate_audit(auth=request.state.auth, data=body)
        return CreateEvalResponse(id=audit.id, status=audit.status)

    async def list_audits(
        self,
        request: Request,
        query_params: Annotated[FilterParams, Query()],
    ) -> AuditsResponse:
        # rate_limit(request=request, user=user)
        audit_service = AuditService()
        response = await audit_service.get_audits(
            auth=request.state.auth,
            query=query_params,
        )

        return response

    async def get_audit(self, request: Request, id: str) -> AuditResponse:
        audit_service = AuditService()

        try:
            audit = await audit_service.get_audit(auth=request.state.auth, id=id)
            return audit
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
            statuses = await audit_service.get_status(auth=request.state.auth, id=id)
            return statuses
        except DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="this audit does not exist under these credentials",
            )

    async def submit_feedback(
        self, request: Request, body: Annotated[FeedbackBody, Body()], id: str
    ) -> BooleanResponse:
        audit_service = AuditService()
        await audit_service.submit_feedback(data=body, auth=request.state.auth, id=id)
        return BooleanResponse(success=True)

    async def game(self):
        try:
            game_worker.run(
                "generate a smart contract audit for mainnet"
                " contract 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
            )
            return BooleanResponse(success=True)
        except Exception as err:
            logfire.exception(str(err))
            return BooleanResponse(success=False)
