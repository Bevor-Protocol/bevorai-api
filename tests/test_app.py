import pytest
import pytest_asyncio

from app.api.app.interface import AppUpsertBody
from app.api.user.service import UserService
from app.db.models import App, Audit, Contract, Permission
from app.utils.types.enums import AuditTypeEnum, ContractMethodEnum, NetworkEnum
from tests.constants import FIRST_PARTY_APP_API_KEY, THIRD_PARTY_APP_API_KEY

USER_WITH_PERMISSIONS_ADDRESS = "0xuserwithcredits"
USER_WITH_PERMISSIONS_API_KEY = "user-with-credits-api-key"


@pytest_asyncio.fixture(scope="module")
async def user_with_permission():
    """Create a user who requested an API key"""
    user_service = UserService()
    # auth_service = AuthService()

    user = await user_service.get_or_create(USER_WITH_PERMISSIONS_ADDRESS)
    permissions = await Permission.get(user_id=user.id)

    # currently done manually.
    permissions.can_create_api_key = True
    permissions.can_create_app = True
    await permissions.save()

    return user


@pytest.mark.anyio
async def test_create_app_no_user_header(third_party_app, async_client):
    """only 1st party app can create"""
    body = AppUpsertBody(name="test")
    response = await async_client.post(
        "/app",
        headers={"Authorization": f"Bearer {THIRD_PARTY_APP_API_KEY}"},
        json=body.model_dump(),
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_create_app_user_no_permission(
    first_party_app, standard_user, async_client
):
    """user must have permissions"""
    body = AppUpsertBody(name="test")
    response = await async_client.post(
        "/app",
        headers={
            "Authorization": f"Bearer {FIRST_PARTY_APP_API_KEY}",
            "Bevor-User-Identifier": str(standard_user.id),
        },
        json=body.model_dump(),
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_create_app(first_party_app, user_with_permission, async_client):
    body = AppUpsertBody(name="test")
    response = await async_client.post(
        "/app",
        headers={
            "Authorization": f"Bearer {FIRST_PARTY_APP_API_KEY}",
            "Bevor-User-Identifier": str(user_with_permission.id),
        },
        json=body.model_dump(),
    )
    assert response.status_code == 202
    app = await App.get(owner_id=user_with_permission.id)
    app_permissions = await Permission.get(app_id=app.id)
    assert app.name == "test"
    assert app_permissions.can_create_api_key is True

    await app.delete()
    assert not await Permission.exists(app_id=app.id)  # ensure cascade


@pytest.mark.anyio
async def test_return_when_app_exists(first_party_app, user_with_app, async_client):
    assert App.exists(owner_id=user_with_app.id)

    body = AppUpsertBody(name="test")
    response = await async_client.post(
        "/app",
        headers={
            "Authorization": f"Bearer {FIRST_PARTY_APP_API_KEY}",
            "Bevor-User-Identifier": str(user_with_app.id),
        },
        json=body.model_dump(),
    )
    assert response.status_code == 202

    app = await App.filter(owner_id=user_with_app.id)
    assert len(app) == 1


@pytest.mark.anyio
async def test_update_app(first_party_app, user_with_permission, async_client):
    NAME = "Test App"
    UPDATED_NAME = "Updated Test App"

    # First create an app
    body = AppUpsertBody(name=NAME)
    response = await async_client.post(
        "/app",
        headers={
            "Authorization": f"Bearer {FIRST_PARTY_APP_API_KEY}",
            "Bevor-User-Identifier": str(user_with_permission.id),
        },
        json=body.model_dump(),
    )
    assert response.status_code == 202

    # Now update it
    update_body = AppUpsertBody(name=UPDATED_NAME)
    response = await async_client.patch(
        "/app",
        headers={
            "Authorization": f"Bearer {FIRST_PARTY_APP_API_KEY}",
            "Bevor-User-Identifier": str(user_with_permission.id),
        },
        json=update_body.model_dump(),
    )
    assert response.status_code == 202
    data = response.json()
    assert data["success"] is True  # type: ignore

    # Verify the app was updated
    app = await App.get(name=UPDATED_NAME)
    assert app.name == UPDATED_NAME
    await app.delete()


@pytest.mark.anyio
async def test_get_app_info(third_party_app, async_client):
    """3rd party app fixture has app and its owner already created"""
    response = await async_client.get(
        "/app/info",
        headers={
            "Authorization": f"Bearer {THIRD_PARTY_APP_API_KEY}",
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Verify app info fields
    assert data["id"] == str(third_party_app.id)  # type: ignore
    assert data["name"] == third_party_app.name  # type: ignore
    assert "created_at" in data
    assert data["n_contracts"] == 0  # type: ignore
    assert data["n_audits"] == 0  # type: ignore


@pytest.mark.anyio
async def test_get_app_info_extended(third_party_app, async_client):
    """3rd party app fixture has app and its owner already created"""
    contract = await Contract.create(
        address="0xTESTCONTRACT",
        network=NetworkEnum.ETH,
        method=ContractMethodEnum.SCAN,
        code="contract Test {}",
        is_available=True,
    )
    await Audit.create(
        contract=contract,
        app=third_party_app,
        audit_type=AuditTypeEnum.GAS,
    )
    await Audit.create(
        contract=contract,
        app=third_party_app,
        audit_type=AuditTypeEnum.SECURITY,
    )

    response = await async_client.get(
        "/app/info",
        headers={
            "Authorization": f"Bearer {THIRD_PARTY_APP_API_KEY}",
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Verify app info fields
    assert data["id"] == str(third_party_app.id)  # type: ignore
    assert data["name"] == third_party_app.name  # type: ignore
    assert "created_at" in data
    assert data["n_contracts"] == 1  # type: ignore
    assert data["n_audits"] == 2  # type: ignore

    await Audit.filter(contract_id=contract.id).delete()
    await contract.delete()


@pytest.mark.anyio
async def test_get_app_stats(first_party_app, async_client):
    response = await async_client.get(
        "/app/stats",
        headers={"Authorization": f"Bearer {FIRST_PARTY_APP_API_KEY}"},
    )
    assert response.status_code == 200
    data = response.json()

    # Verify stats fields exist
    assert "n_apps" in data
    assert isinstance(data["n_apps"], int)  # type: ignore
    assert len(data["users_timeseries"]) > 0  # due to fixtures # type: ignore
