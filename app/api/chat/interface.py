from typing import TypedDict

from pydantic import BaseModel


class ChatBody(BaseModel):
    message: str


class ChatMessageDict(TypedDict):
    id: str
    role: str
    timestamp: str
    content: str
