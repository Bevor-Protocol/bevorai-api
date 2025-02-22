from tortoise.query_utils import Prefetch
from tortoise.transactions import in_transaction

from app.api.core.dependencies import AuthState
from app.db.models import App, Audit, Auth, Permission, User
from app.schema.response import AppInfo, AuthInfo, UserInfo, UserInfoResponse
from app.utils.enums import AuditStatusEnum, ClientTypeEnum


class UserService:
    async def upsert_user(self, auth: AuthState, address: str) -> User:
        user = await User.filter(app_owner_id=auth.app_id, address=address).first()
        if user:
            return user

        async with in_transaction():
            user = await User.create(app_owner_id=auth.app_id, address=address)
            await Permission.create(client_type=ClientTypeEnum.USER, user_id=user.id)

        return user

    async def get_user_info(self, auth: AuthState) -> UserInfoResponse:

        audit_queryset = Audit.filter(status=AuditStatusEnum.SUCCESS).select_related(
            "contract"
        )

        app_queryset = App.all().prefetch_related("permissions", "auth")

        audit_pf = Prefetch("audits", queryset=audit_queryset)
        app_pf = Prefetch("app", queryset=app_queryset)

        cur_user = await User.get(id=auth.user_id).prefetch_related(
            audit_pf, "auth", "permissions", app_pf
        )

        user_audits = cur_user.audits
        user_auth = cur_user.auth
        # this is a nullable FK relation, grab the first.
        user_app: App | None = cur_user.app[0] if cur_user.app else None
        # currently only 1 auth is support per user, but it's not a OneToOne relation
        user_permissions: Permission = cur_user.permissions

        app_info = AppInfo(
            exists=user_app is not None,
            can_create=user_permissions.can_create_app,
        )

        if user_app:
            auth: Auth | None = user_app.auth
            permissions: Permission | None = user_app.permissions
            app_info.name = user_app.name
            app_info.exists_auth = auth is not None
            if permissions:
                app_info.can_create_auth = permissions.can_create_api_key

        n_audits = len(user_audits)
        n_contracts = len(set(map(lambda x: x.contract.id, user_audits)))

        return UserInfoResponse(
            user=UserInfo(
                id=cur_user.id,
                address=cur_user.address,
                created_at=cur_user.created_at,
                total_credits=cur_user.total_credits,
                remaining_credits=cur_user.total_credits - cur_user.used_credits,
            ),
            auth=AuthInfo(
                exists=user_auth is not None,
                is_active=not user_auth.revoked_at if user_auth else False,
                can_create=user_permissions.can_create_api_key,
            ),
            app=app_info,
            n_contracts=n_contracts,
            n_audits=n_audits,
        )
