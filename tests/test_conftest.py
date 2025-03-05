import logging

import pytest

from app.db.models import App, User
from app.utils.types.enums import AppTypeEnum

# @pytest.mark.asyncio
# async def test_database_initialization():
#     """Test that the database is properly initialized"""

#     auth = await App.filter(type=AppTypeEnum.FIRST_PARTY).first()

#     assert auth
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_user_factory(user_factory):
    """Test that the user factory creates users correctly"""
    user: User = await user_factory(address="0xtest", total_credits=50.0)
    assert user.address == "0xtest"
    assert user.total_credits == 50.0
    assert user.used_credits == 0.0

    await user.delete()


@pytest.mark.asyncio
async def test_app_factory(app_factory, user_factory):
    """Test that the app factory creates apps correctly"""
    owner: User = await user_factory(address="0xtest")
    app: App = await app_factory(
        name="Test Factory App", app_type=AppTypeEnum.THIRD_PARTY, owner=owner
    )
    assert app.name == "Test Factory App"
    assert app.type == AppTypeEnum.THIRD_PARTY
    assert app.owner.id == owner.id

    await owner.delete()
    await app.delete()


@pytest.mark.asyncio
async def test_third_party_app_requires_user(app_factory):
    """Test that creating a third-party app without an owner raises an exception"""
    with pytest.raises(Exception) as excinfo:
        await app_factory(name="Test App", app_type=AppTypeEnum.THIRD_PARTY)

    assert "owner_address is required" in str(excinfo.value)


@pytest.mark.asyncio
async def test_session_apps_exist(first_party_app, third_party_app):
    # duplicative, but include either way. Removing the params would call this to fail.

    first_party = await App.get(name="test").select_related("owner")
    third_party = await App.get(name="Third Party Test App").select_related("owner")

    assert first_party.owner is None
    assert first_party.type == AppTypeEnum.FIRST_PARTY
    assert third_party.owner is not None
    assert third_party.type == AppTypeEnum.THIRD_PARTY
