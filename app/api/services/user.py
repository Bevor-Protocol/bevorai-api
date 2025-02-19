from tortoise.query_utils import Prefetch

from app.api.core.dependencies import AuthState
from app.db.models import App, Audit, Auth, Permission, User
from app.schema.response import (
    AnalyticsAudit,
    AnalyticsContract,
    AppInfo,
    AuthInfo,
    UserInfo,
    UserInfoResponse,
)
from app.utils.enums import AuditStatusEnum


class UserService:
    async def upsert_user(self, auth: AuthState, address: str) -> User:
        user = await User.filter(app_owner_id=auth.app_id, address=address).first()
        if user:
            return user

        user = await User.create(app_owner_id=auth.app_id, address=address)

        return user

    async def get_user_info(self, auth: AuthState):

        audit_queryset = (
            Audit.filter(status=AuditStatusEnum.SUCCESS)
            .order_by("-created_at")
            .select_related("contract")
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

        recent_audits = []
        audit: Audit
        for i, audit in enumerate(user_audits[:5]):
            contract = AnalyticsContract(
                id=audit.contract.id,
                method=audit.contract.method,
                address=audit.contract.address,
                network=audit.contract.network,
            )
            response = AnalyticsAudit(
                n=i,
                id=audit.id,
                created_at=audit.created_at,
                app_id=audit.app_id,
                user_id=cur_user.address,
                audit_type=audit.audit_type,
                status=audit.status,
                contract=contract,
            )
            recent_audits.append(response)

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
            audits=recent_audits,
            n_contracts=n_contracts,
            n_audits=n_audits,
        )
