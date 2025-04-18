from typing import Annotated

from fastapi import (
    APIRouter,
    Body,
    Depends,
    Request,
    status,
)
from fastapi.responses import StreamingResponse

from app.api.chat.interface import ChatBody, ChatMessageDict
from app.api.chat.service import ChatService
from app.api.dependencies import Authentication
from app.utils.openapi_tags import AUDIT_TAG
from app.utils.types.enums import RoleEnum
from app.utils.types.relations import ChatRelation
from app.utils.types.shared import IdResponse, ResultsResponse


class ChatRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/chat", tags=[AUDIT_TAG])

        self.add_api_route(
            "/initiate/{audit_id}",
            self.initiate_chat,
            methods=["POST"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
            status_code=status.HTTP_202_ACCEPTED,
        )

        self.add_api_route(
            "/list",
            self.get_chats,
            methods=["GET"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
            status_code=status.HTTP_200_OK,
        )

        self.add_api_route(
            "/{chat_id}",
            self.chat,
            methods=["POST"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
            status_code=status.HTTP_202_ACCEPTED,
        )

        self.add_api_route(
            "/{chat_id}",
            self.get_chat,
            methods=["GET"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
            status_code=status.HTTP_202_ACCEPTED,
        )

    async def initiate_chat(self, request: Request, audit_id: str):
        chat_service = ChatService()
        chat = await chat_service.initiate_chat(
            auth=request.state.auth, audit_id=audit_id
        )

        return IdResponse(id=chat.id)

    async def get_chats(self, request: Request) -> ResultsResponse[ChatRelation]:
        chat_service = ChatService()
        chats = await chat_service.get_chats(auth=request.state.auth)

        chat_objects = list(map(ChatRelation.model_validate, chats))

        return ResultsResponse[ChatRelation](results=chat_objects)

    async def get_chat(
        self, request: Request, chat_id: str
    ) -> ResultsResponse[ChatMessageDict]:
        chat_service = ChatService()
        messages = await chat_service.get_chat_messages(
            auth=request.state.auth, chat_id=chat_id
        )

        return ResultsResponse[ChatMessageDict](results=messages)

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
