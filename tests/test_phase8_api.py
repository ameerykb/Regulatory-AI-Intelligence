from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_invalid_impact_id():
    response = client.get("/impact/invalid-id")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid comparison ID"


def test_invalid_json_download():
    response = client.get(
        "/impact/invalid-id/download?format=json"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid comparison ID"


def test_invalid_markdown_download():
    response = client.get(
        "/impact/invalid-id/download?format=md"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid comparison ID"


def test_invalid_analysis_id():
    response = client.post(
        "/impact/invalid-id/analyze"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid comparison ID"
