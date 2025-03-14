import pytest

from app.db.models import User
from app.utils.schema.request import UserUpsertBody
from tests.constants import (
    FIRST_PARTY_APP_API_KEY,
    THIRD_PARTY_APP_API_KEY,
    USER_API_KEY,
)


@pytest.mark.anyio
async def test_api_create_user(first_party_app, async_client):
    ADDRESS = "0xtest"
    assert not await User.exists(address=ADDRESS)

    body = UserUpsertBody(address=ADDRESS)
    response = await async_client.post(
        "/user",
        headers={"Authorization": f"Bearer {FIRST_PARTY_APP_API_KEY}"},
        json=body.model_dump(),
    )
    assert response.status_code == 202
    data = response.json()
    assert data["id"] is not None  # type: ignore

    user = await User.get(address=ADDRESS)
    await user.delete()


@pytest.mark.anyio
async def test_api_creates_one_user(first_party_app, async_client):
    ADDRESS = "0xtest"
    assert not await User.exists(address=ADDRESS)

    body = UserUpsertBody(address=ADDRESS)
    response = await async_client.post(
        "/user",
        headers={"Authorization": f"Bearer {FIRST_PARTY_APP_API_KEY}"},
        json=body.model_dump(),
    )
    assert response.status_code == 202
    data = response.json()
    assert data["id"] is not None  # type: ignore

    # calls again, should not create.
    response = await async_client.post(
        "/user",
        headers={"Authorization": f"Bearer {FIRST_PARTY_APP_API_KEY}"},
        json=body.model_dump(),
    )

    assert response.status_code == 202
    get_data = response.json()
    assert get_data["id"] is not None  # type: ignore
    assert get_data["id"] == data["id"]  # type: ignore

    users = await User.filter(address=ADDRESS)
    assert len(users) == 1

    await users[0].delete()


@pytest.mark.anyio
async def test_api_create_user_should_fail(user_with_auth, async_client):
    assert not await User.exists(address="0xtest")

    body = UserUpsertBody(address="0xtest")
    response = await async_client.post(
        "/user",
        headers={"Authorization": f"Bearer {USER_API_KEY}"},
        json=body.model_dump(),
    )
    assert response.status_code == 401

    # Verify user was not created
    assert not await User.exists(address="0xtest")


@pytest.mark.anyio
async def test_api_create_user_from_third_party(third_party_app, async_client):
    ADDRESS = "0xtest"
    assert not await User.exists(address=ADDRESS)

    body = UserUpsertBody(address=ADDRESS)
    response = await async_client.post(
        "/user",
        headers={"Authorization": f"Bearer {THIRD_PARTY_APP_API_KEY}"},
        json=body.model_dump(),
    )
    assert response.status_code == 202
    data = response.json()
    assert data["id"] is not None  # type: ignore

    user = await User.get(address=ADDRESS)
    await user.delete()


@pytest.mark.anyio
async def test_api_get_user_info_as_user(user_with_auth, async_client):
    """Test user calling on behalf of themselves"""
    user_id = str(user_with_auth.id)

    response = await async_client.get(
        "/user/info",
        headers={"Authorization": f"Bearer {USER_API_KEY}"},
    )
    assert response.status_code == 200
    data = response.json()

    # Verify all fields from UserInfoResponse are present and correct
    assert data["id"] == user_id  # type: ignore
    assert data["address"] == user_with_auth.address  # type: ignore
    assert "created_at" in data
    assert data["total_credits"] == user_with_auth.total_credits  # type: ignore
    assert (
        data["remaining_credits"]  # type: ignore
        == user_with_auth.total_credits - user_with_auth.used_credits
    )

    # Verify auth info
    assert "auth" in data
    assert (
        data["auth"]["exists"] is True  # type: ignore
    )  # Since we're using user_with_auth fixture
    assert (
        data["auth"]["is_active"] is True  # type: ignore
    )  # Since we're using user_with_auth fixture
    assert (
        data["auth"]["can_create"] is True  # type: ignore
    )  # Since we're using user_with_auth fixture

    # Verify app info
    assert "app" in data
    assert "exists" in data["app"]  # type: ignore
    assert "can_create" in data["app"]  # type: ignore

    # Verify audit counts
    assert data["n_contracts"] == 0  # haven't created any yet. # type: ignore
    assert data["n_audits"] == 0  # haven't created any yet. # type: ignore


@pytest.mark.anyio
async def test_api_get_user_info_as_app(third_party_app, async_client):
    """Test app calling on behalf of themselves"""
    response = await async_client.get(
        "/user/info",
        headers={"Authorization": f"Bearer {THIRD_PARTY_APP_API_KEY}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(third_party_app.owner_id)  # type: ignore


@pytest.mark.anyio
async def test_api_get_user_info_as_app_for_user(
    standard_user, third_party_app, async_client
):
    """Test app calling on behalf of user"""

    response = await async_client.get(
        "/user/info",
        headers={
            "Authorization": f"Bearer {THIRD_PARTY_APP_API_KEY}",
            "Bevor-User-Identifier": str(standard_user.id),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(standard_user.id)  # type: ignore
