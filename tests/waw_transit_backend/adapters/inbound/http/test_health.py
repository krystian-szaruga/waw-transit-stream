from fastapi.testclient import TestClient


def test_when_health_is_requested_then_status_is_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
