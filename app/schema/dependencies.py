from typing import Optional, TypedDict

from app.db.models import App, User


class UserDict(TypedDict):
    user: Optional[User]
    app: Optional[App]
    require_credit_and_limit: bool
