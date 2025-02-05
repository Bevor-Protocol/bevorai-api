from app.api.analytics.audits import get_audits
from app.api.depends.auth import UserDict
from app.db.models import App, Auth, User
from app.pydantic.response import AppInfo, AuthInfo, UserInfo, UserInfoResponse
from app.utils.typed import FilterParams


async def get_user_info(user: UserDict):

    cur_user = await User.get(id=user["user"].id)
    user_auth = await Auth.filter(user_id=user["user"].id).first()
    app = await App.filter(owner_id=cur_user.id).first()

    audits = await get_audits(
        user, FilterParams(page=0, page_size=10, user_id=cur_user.address)
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
        app=AppInfo(exists=app is not None, name=app.name if app is not None else None),
        audits=audits.results,
        n_contracts=n_contracts,
    )
