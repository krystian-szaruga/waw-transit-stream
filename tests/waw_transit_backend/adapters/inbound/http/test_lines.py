from fastapi.testclient import TestClient


def test_when_listing_lines_then_active_version_lines_are_returned(client: TestClient) -> None:
    response = client.get("/lines")

    assert response.status_code == 200
    assert response.json() == [
        {"name": "175", "vehicle_type": 1},
        {"name": "9", "vehicle_type": 2},
    ]
