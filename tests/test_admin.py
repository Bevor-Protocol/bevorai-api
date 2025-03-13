import pytest
import pytest_asyncio

from app.api.auth.service import AuthService
from app.api.user.service import UserService
from app.db.models import Auth, Permission
from app.utils.schema.dependencies import AuthState
from app.utils.types.enums import AuthScopeEnum, ClientTypeEnum, RoleEnum
from tests.constants import FIRST_PARTY_APP_API_KEY

USER_WITH_ADMIN_ADDRESS = "0xuserwithadmin"
USER_WITH_ADMIN_API_KEY = "user-with-admin-api-key"


@pytest_asyncio.fixture(scope="module")
async def user_with_auth_and_admin():
    """Create a user who requested an API key"""
    user_service = UserService()
    auth_service = AuthService()

    user = await user_service.get_or_create(USER_WITH_ADMIN_ADDRESS)
    user.total_credits = 100.0
    await user.save()
    permissions = await Permission.get(user_id=user.id)

    # currently done manually.
    permissions.can_create_api_key = True
    permissions.can_create_app = True

    await permissions.save()

    mock_auth_state = AuthState(
        user_id=user.id,
        consumes_credits=True,
        credit_consumer_user_id=user.id,
        role=RoleEnum.USER,
    )

    intermediate_key = await auth_service.generate(
        auth_obj=mock_auth_state, client_type=ClientTypeEnum.USER
    )

    assert len(intermediate_key)

    # can't pass key to service. explicitly update it to known value.
    hashed_key = Auth.hash_key(USER_WITH_ADMIN_API_KEY)
    auth = await Auth.get(user_id=user.id)
    auth.hashed_key = hashed_key
    auth.scope = AuthScopeEnum.ADMIN
    await auth.save()

    return user


@pytest.mark.anyio
async def test_is_admin(
    async_client, first_party_app, user_with_auth, user_with_auth_and_admin
):
    """
    should resolve to a boolean
    """
    response = await async_client.get(
        "/admin/status",
        headers={
            "Authorization": f"Bearer {FIRST_PARTY_APP_API_KEY}",
            "Bevor-User-Identifier": str(user_with_auth.id),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False

    response = await async_client.get(
        "/admin/status",
        headers={
            "Authorization": f"Bearer {FIRST_PARTY_APP_API_KEY}",
            "Bevor-User-Identifier": str(user_with_auth_and_admin.id),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.anyio
async def test_fail_if_not_admin(
    async_client, first_party_app, user_with_auth_and_admin, user_with_auth
):
    """
    should fail if not admin
    """
    response = await async_client.get(
        "/admin/search/app",
        headers={
            "Authorization": f"Bearer {FIRST_PARTY_APP_API_KEY}",
            "Bevor-User-Identifier": str(user_with_auth.id),
        },
    )
    assert response.status_code == 401

    response = await async_client.get(
        "/admin/search/app",
        headers={
            "Authorization": f"Bearer {FIRST_PARTY_APP_API_KEY}",
            "Bevor-User-Identifier": str(user_with_auth_and_admin.id),
        },
    )
    assert response.status_code == 200

    response = await async_client.get(
        "/admin/search/app?identifier=123",
        headers={
            "Authorization": f"Bearer {FIRST_PARTY_APP_API_KEY}",
            "Bevor-User-Identifier": str(user_with_auth_and_admin.id),
        },
    )
    assert response.status_code == 200
