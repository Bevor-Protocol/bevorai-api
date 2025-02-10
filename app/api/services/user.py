from tortoise.query_utils import Prefetch

from app.api.core.dependencies import AuthDict
from app.db.models import App, Audit, Permission, User
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
    async def upsert_user(self, auth: AuthDict, address: str) -> User:
        user = await User.filter(app_owner_id=auth["app"].id, address=address).first()
        if user:
            return user

        user = await User.create(app_owner_id=auth["app"].id, address=address)

        return user

    async def get_user_info(self, user: AuthDict):

        audit_queryset = (
            Audit.filter(status=AuditStatusEnum.SUCCESS)
            .order_by("-created_at")
            .select_related("contract")
        )

        audit_pf = Prefetch("audits", queryset=audit_queryset)

        cur_user = await User.get(id=user["user"].id).prefetch_related(
            audit_pf, "auth", "permissions"
        )
        user_app = (
            await App.filter(owner_id=user["user"].id)
            .prefetch_related("auth", "permissions")
            .first()
        )

        user_audits = cur_user.audits
        # currently only 1 auth is support per user, but it's not a OneToOne relation
        user_auth = cur_user.auth[0]
        user_permissions: Permission = cur_user.permissions
        user_app_permissions: Permission | None = (
            user_app.permissions if user_app else None
        )

        app_info = AppInfo(
            exists=user_app is not None,
            name=user_app.name if user_app else None,
            can_create=user_permissions.can_create_app,
        )

        if user_app and user_app_permissions:
            app_info.exists_auth = user_app.auth is not None
            app_info.can_create_auth = user_app_permissions.can_create_api_key

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
                remaining_credits=cur_user.remaining_credits,
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
