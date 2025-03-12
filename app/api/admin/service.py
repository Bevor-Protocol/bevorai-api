from tortoise.expressions import Q

from app.db.models import App, Auth, Permission, User
from app.utils.helpers.model_parser import cast_app, cast_user
from app.utils.schema.dependencies import AuthState
from app.utils.schema.request import UpdatePermissionsBody
from app.utils.types.enums import AuthScopeEnum, ClientTypeEnum


class AdminService:

    async def is_admin(self, auth_state: AuthState):
        auth = await Auth.get(user_id=auth_state.user_id)
        return auth.scope == AuthScopeEnum.ADMIN

    async def update_permissions(
        self, id: str, client_type: ClientTypeEnum, body: UpdatePermissionsBody
    ):
        filter = {"client_type": client_type}
        if type == ClientTypeEnum.APP:
            filter["app_id"] = id
        else:
            filter["user_id"] = id
        permissions = await Permission.get(**filter)
        permissions.can_create_api_key = body.can_create_api_key
        permissions.can_create_app = body.can_create_app
        await permissions.save()

    async def search_users(self, identifier: str):
        """
        Search for users by either their UUID or address.

        Args:
            identifier: A string that could be either a UUID or an address

        Returns:
            The user object if found, None otherwise
        """
        # Use OR clause to search by ID or address with partial matching

        users = await User.filter(
            Q(id__icontains=identifier) | Q(address__icontains=identifier)
        ).all()

        return list(map(lambda x: cast_user(x).model_dump(), users))

    async def search_apps(self, identifier: str):
        """
        Search for users by either their UUID or address.

        Args:
            identifier: A string that could be either a UUID or an address

        Returns:
            The user object if found, None otherwise
        """
        # Use OR clause to search by ID or address with partial matching

        apps = await App.filter(id__icontains=identifier).all()

        return list(map(lambda x: cast_app(x).model_dump(), apps))
