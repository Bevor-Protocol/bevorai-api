from tortoise.transactions import in_transaction

from app.api.dependencies import AuthState
from app.api.permission.service import PermissionService
from app.db.models import App, Audit, Auth, Permission, User
from app.utils.types.enums import AuditStatusEnum, ClientTypeEnum
from app.utils.types.models import UserSchema

from .interface import AuthInfo, UserAppInfo, UserInfoResponse


class UserService:
    async def get_or_create(self, address: str) -> User:
        user = await User.filter(address=address).first()
        if user:
            return user

        permission_service = PermissionService()
        async with in_transaction():
            user = await User.create(address=address)
            await permission_service.create(
                client_type=ClientTypeEnum.USER, identifier=user.id
            )

        return user

    async def get_info(self, auth: AuthState) -> UserInfoResponse:
        # prefetching caused asyncio.lock errors when running all tests
        # despite each testing module working in isolation. Ill just call
        # each query individually.
        cur_user = await User.get(id=auth.user_id)
        user_audits = await Audit.filter(
            user_id=auth.user_id, status=AuditStatusEnum.SUCCESS
        )
        user_auth = await Auth.filter(user_id=auth.user_id).first()
        user_app = (
            await App.filter(owner_id=auth.user_id)
            .select_related("permissions", "auth")
            .first()
        )
        user_permissions = await Permission.get(user_id=auth.user_id)

        app_info = UserAppInfo(
            exists=user_app is not None,
            can_create=user_permissions.can_create_app,
        )

        if user_app:
            user_app_auth: Auth | None = user_app.auth
            permissions: Permission | None = user_app.permissions
            app_info.name = user_app.name
            app_info.exists_auth = user_app_auth is not None
            if permissions:
                app_info.can_create_auth = permissions.can_create_api_key

        n_audits = len(user_audits)
        n_contracts = len(set(map(lambda x: x.contract_id, user_audits)))

        return UserInfoResponse(
            **UserSchema.model_validate(cur_user).model_dump(),
            total_credits=cur_user.total_credits,
            remaining_credits=cur_user.total_credits - cur_user.used_credits,
            auth=AuthInfo(
                exists=user_auth is not None,
                is_active=not user_auth.revoked_at if user_auth else False,
                can_create=user_permissions.can_create_api_key,
            ),
            app=app_info,
            n_contracts=n_contracts,
            n_audits=n_audits,
        )
