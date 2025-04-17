import asyncio
import os
import sys
from typing import AsyncGenerator

import pytest_asyncio

from app.api.app.interface import AppUpsertBody
from app.api.app.service import AppService
from app.api.auth.service import AuthService
from app.api.user.service import UserService
from tests.constants import (
    FIRST_PARTY_APP_API_KEY,
    FIRST_PARTY_APP_NAME,
    STANDARD_USER_ADDRESS,
    THIRD_PARTY_APP_API_KEY,
    THIRD_PARTY_APP_NAME,
    THIRD_PARTY_APP_OWNER_ADDRESS,
    USER_API_KEY,
    USER_WITH_APP_API_KEY,
    USER_WITH_AUTH_ADDRESS,
    USER_WITH_PERMISSION_ADDRESS,
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logfire
import pytest
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from app.db.models import App, Auth, Permission, User  # Replace with your actual model
from app.main import app
from app.utils.types.enums import AppTypeEnum, AuthScopeEnum, ClientTypeEnum, RoleEnum
from app.utils.types.shared import AuthState

logfire.configure(local=True, send_to_logfire=False)

TEST_DB_URL = "sqlite://:memory:"

TEST_TORTOISE_ORM = {
    "connections": {"default": TEST_DB_URL},
    "apps": {
        "models": {
            "models": ["app.db.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}


@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def in_memory_db(request, event_loop):
    # Initialize the in-memory database
    event_loop.run_until_complete(Tortoise.init(config=TEST_TORTOISE_ORM))
    # Generate schemas with safe=True to handle cyclic dependencies
    event_loop.run_until_complete(Tortoise.generate_schemas(safe=True))

    def finalizer():
        event_loop.run_until_complete(Tortoise._drop_databases())
        event_loop.run_until_complete(Tortoise.close_connections())

    request.addfinalizer(finalizer)


@pytest.fixture(scope="module")
async def async_client() -> AsyncGenerator:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


"""
Creating core fixtures to be used throughout. I'll never manipulate these.

If I do need to manipulate them, they'll be scoped within a module.
"""


@pytest_asyncio.fixture(scope="session")
async def first_party_app() -> App:
    """does not require a user (app owner)"""
    app = await App.create(name=FIRST_PARTY_APP_NAME, type=AppTypeEnum.FIRST_PARTY)
    hashed_key = Auth.hash_key(FIRST_PARTY_APP_API_KEY)
    await Auth.create(
        app=app,
        client_type=ClientTypeEnum.APP,
        hashed_key=hashed_key,
        consumes_credits=False,
        scope=AuthScopeEnum.ADMIN,
    )
    return app


@pytest_asyncio.fixture(scope="session")
async def standard_user() -> User:
    """Create a standard user"""
    user_service = UserService()

    user = await user_service.get_or_create(STANDARD_USER_ADDRESS)
    permissions = await Permission.get(user_id=user.id)

    assert not permissions.can_create_api_key
    assert not permissions.can_create_app

    return user


@pytest_asyncio.fixture(scope="session")
async def user_with_permission() -> User:
    """Create a user where permissions were whitelisted"""
    user_service = UserService()

    user = await user_service.get_or_create(USER_WITH_PERMISSION_ADDRESS)
    permissions = await Permission.get(user_id=user.id)

    # currently done manually.
    permissions.can_create_api_key = True
    permissions.can_create_app = True

    await permissions.save()

    return user


@pytest_asyncio.fixture(scope="session")
async def user_with_auth() -> User:
    """Create a user who requested an API key"""
    user_service = UserService()
    auth_service = AuthService()

    user = await user_service.get_or_create(USER_WITH_AUTH_ADDRESS)
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
    hashed_key = Auth.hash_key(USER_API_KEY)
    auth = await Auth.get(user_id=user.id)
    auth.hashed_key = hashed_key
    await auth.save()

    return user


@pytest_asyncio.fixture(scope="session")
async def user_with_app() -> User:
    """Create a user who created an App"""
    user_service = UserService()
    auth_service = AuthService()

    user = await user_service.get_or_create(THIRD_PARTY_APP_OWNER_ADDRESS)
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
    hashed_key = Auth.hash_key(USER_WITH_APP_API_KEY)
    auth = await Auth.get(user_id=user.id)
    auth.hashed_key = hashed_key
    await auth.save()

    return user


@pytest_asyncio.fixture(scope="session")
async def third_party_app(user_with_app) -> App:
    app_service = AppService()
    auth_service = AuthService()

    mock_auth_state = AuthState(
        user_id=user_with_app.id,
        consumes_credits=True,
        credit_consumer_user_id=user_with_app.id,
        role=RoleEnum.USER,
    )

    await app_service.create(
        auth=mock_auth_state, body=AppUpsertBody(name=THIRD_PARTY_APP_NAME)
    )

    app = await App.get(owner_id=user_with_app.id)

    intermediate_key = await auth_service.generate(
        auth_obj=mock_auth_state, client_type=ClientTypeEnum.APP
    )

    assert len(intermediate_key)

    # can't pass key to service. explicitly update it to known value.
    hashed_key = Auth.hash_key(THIRD_PARTY_APP_API_KEY)
    auth = await Auth.get(app_id=app.id)
    auth.hashed_key = hashed_key
    await auth.save()

    return app
