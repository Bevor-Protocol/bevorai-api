import pytest
from app.api.routers.health import BaseRouter
from tortoise import Tortoise

@pytest.mark.asyncio
async def test_read_root_unauthorized():
    router = BaseRouter()
    response = await router.read_root()
    assert response == {"Hello": "World"}

@pytest.mark.asyncio
async def test_health_check_healthy(mocker):
    # Mock the Tortoise.get_connection method
    mock_connection = mocker.Mock()
    mock_connection.execute_query = mocker.AsyncMock(return_value=None)
    mocker.patch('tortoise.Tortoise.get_connection', return_value=mock_connection)

    router = BaseRouter()
    response = await router.health_check()
    assert response["status"] == "healthy"

@pytest.mark.asyncio
async def test_health_check_unhealthy():
    router = BaseRouter()
    # Simulate a failure in the database connection
    Tortoise.get_connection = lambda _: None
    response = await router.health_check()
    assert response["status"] == "unhealthy"
    assert "error" in response
