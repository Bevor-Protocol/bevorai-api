from typing import Annotated

from fastapi import (
    APIRouter,
    Body,
    Depends,
    Request,
    status,
)
from fastapi.responses import StreamingResponse

from app.api.chat.interface import ChatBody
from app.api.chat.service import ChatService
from app.api.dependencies import Authentication
from app.utils.openapi_tags import AUDIT_TAG
from app.utils.types.enums import RoleEnum
from app.utils.types.shared import IdResponse


class AuditRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/chat", tags=[AUDIT_TAG])

        self.add_api_route(
            "/{audit_id}",
            self.initiate_chat,
            methods=["POST"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
            status_code=status.HTTP_202_ACCEPTED,
        )

        self.add_api_route(
            "/{chat_id}",
            self.chat,
            methods=["POST"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
            status_code=status.HTTP_202_ACCEPTED,
        )

    async def initiate_chat(self, request: Request, audit_id: str):
        chat_service = ChatService()
        chat = await chat_service.initiate_chat(
            auth=request.auth.state, audit_id=audit_id
        )

        return IdResponse(id=chat.id)

    async def chat(
        self,
        request: Request,
        chat_id: str,
        body: Annotated[ChatBody, Body()],
    ):
        chat_service = ChatService()

        return StreamingResponse(
            chat_service.chat(
                auth=request.state.auth, chat_id=chat_id, message=body.message
            ),
            media_type="text/plain",
        )
