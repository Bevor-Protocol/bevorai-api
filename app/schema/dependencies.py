from typing import Optional, TypedDict

from app.db.models import App, User
from app.utils.enums import AuthScopeEnum, ClientTypeEnum


class AuthDict(TypedDict):
    user: Optional[User] = None
    app: Optional[App] = None
    is_delegator: bool = False
    scope: AuthScopeEnum
    client_type: ClientTypeEnum
