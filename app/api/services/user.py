from app.api.core.dependencies import AuthDict
from app.api.services.audit import AuditService
from app.db.models import App, Auth, User
from app.schema.request import FilterParams
from app.schema.response import AppInfo, AuthInfo, UserInfo, UserInfoResponse


class UserService:
    async def upsert_user(self, auth: AuthDict, address: str) -> User:
        user = await User.filter(app_owner_id=auth["app"].id, address=address).first()
        if user:
            return user

        user = await User.create(app_owner_id=auth["app"].id, address=address)

        return user

    async def get_user_info(self, user: AuthDict):
        audit_service = AuditService()

        cur_user = await User.get(id=user["user"].id)
        user_auth = await Auth.filter(user_id=user["user"].id).first()
        app = await App.filter(owner_id=cur_user.id).first()

        audits = await audit_service.get_audits(
            user, FilterParams(page=0, page_size=10, user_id=cur_user.id)
        )

        n_contracts = len(set(map(lambda x: x.contract.id, audits.results)))

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
                is_active=not user_auth.is_revoked if user_auth else False,
            ),
            app=AppInfo(
                exists=app is not None, name=app.name if app is not None else None
            ),
            audits=audits.results,
            n_contracts=n_contracts,
        )
