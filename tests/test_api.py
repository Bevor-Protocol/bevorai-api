from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_api_docs():
    response = client.get("/docs")
    assert response.status_code == 200

    response = client.get("/redoc")
    assert response.status_code == 200


# @pytest.mark.parametrize(
#     "endpoint",
#     [
#         "/contracts",
#         "/api/platforms",
#         "/api/users",
#     ],
# )
# def test_api_endpoints_require_auth(endpoint):
#     response = client.get(endpoint)
#     assert response.status_code == 401
