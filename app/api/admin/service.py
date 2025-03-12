from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q

from app.db.models import App, Auth, Permission, User
from app.utils.helpers.model_parser import cast_permission
from app.utils.schema.app import AppPydantic
from app.utils.schema.dependencies import AuthState
from app.utils.schema.permission import PermissionPydantic
from app.utils.schema.request import UpdatePermissionsBody
from app.utils.schema.response import (
    AdminAppPermission,
    AdminPermission,
    AdminUserPermission,
)
from app.utils.types.enums import AuthScopeEnum, ClientTypeEnum


class AdminService:

    async def is_admin(self, auth_state: AuthState) -> bool:
        try:
            auth = await Auth.get(user_id=auth_state.user_id)
        except DoesNotExist:
            return False
        return auth.scope == AuthScopeEnum.ADMIN

    async def get_permissions(
        self, id: str, client_type: ClientTypeEnum
    ) -> PermissionPydantic:
        filter = {"client_type": client_type}
        if type == ClientTypeEnum.APP:
            filter["app_id"] = id
        else:
            filter["user_id"] = id
        permission = await Permission.get(**filter)

        return cast_permission(permission)

    async def update_permissions(
        self, id: str, client_type: ClientTypeEnum, body: UpdatePermissionsBody
    ) -> None:
        filter = {"client_type": client_type}
        if type == ClientTypeEnum.APP:
            filter["app_id"] = id
        else:
            filter["user_id"] = id
        permission = await Permission.get(**filter)
        permission.can_create_api_key = body.can_create_api_key
        permission.can_create_app = body.can_create_app
        await permission.save()

    async def search_users(self, identifier: str) -> list[AdminUserPermission]:
        """
        Search for users by either their UUID or address.

        Args:
            identifier: A string that could be either a UUID or an address

        Returns:
            The user object if found, None otherwise
        """
        # Use OR clause to search by ID or address with partial matching

        users = (
            await User.filter(
                Q(id__icontains=identifier) | Q(address__icontains=identifier)
            )
            .prefetch_related("permissions")
            .limit(10)
        )

        results = []
        for user in users:
            permission = None
            if user.permissions:
                user_permission: Permission = user.permissions
                permission = AdminPermission(
                    can_create_api_key=user_permission.can_create_api_key,
                    can_create_app=user_permission.can_create_app,
                )

            results.append(
                AdminUserPermission(
                    id=user.id, address=user.address, permission=permission
                )
            )

        return results

    async def search_apps(self, identifier: str) -> list[AppPydantic]:
        """
        Search for users by either their UUID or address.

        Args:
            identifier: A string that could be either a UUID or an address

        Returns:
            The user object if found, None otherwise
        """
        # Use OR clause to search by ID or address with partial matching

        apps = (
            await App.filter(
                Q(id__icontains=identifier)
                | Q(name__icontains=identifier)
                | Q(owner_id__icontains=identifier)
            )
            .prefetch_related("permissions")
            .limit(10)
        )

        results = []
        for app in apps:
            permission = None
            if app.permissions:
                app_permission: Permission = app.permissions
                permission = AdminPermission(
                    can_create_api_key=app_permission.can_create_api_key,
                    can_create_app=app_permission.can_create_app,
                )

            results.append(
                AdminAppPermission(
                    id=app.id,
                    name=app.name,
                    type=app.type,
                    owner_id=app.owner_id,
                    permission=permission,
                )
            )

        return results
