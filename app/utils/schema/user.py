from pydantic import Field

from .shared import IdResponse


class UserPydantic(IdResponse):
    address: str = Field(description="wallet address of user")
