from fastapi.testclient import TestClient


def test_when_listing_vehicles_then_every_live_vehicle_is_returned(client: TestClient) -> None:
    response = client.get("/vehicles")

    assert response.status_code == 200
    assert {vehicle["id"] for vehicle in response.json()} == {"1:2001", "2:3001"}


def test_when_listing_vehicles_then_the_snapshot_is_mapped_to_the_view(client: TestClient) -> None:
    response = client.get("/vehicles")

    vehicle = next(item for item in response.json() if item["id"] == "1:2001")
    assert vehicle == {
        "id": "1:2001",
        "type": 1,
        "number": "2001",
        "line": "175",
        "brigade": "3",
        "trip_id": "t1",
        "delay_sec": 45.5,
        "status": "MATCHED",
        "next_stop": "Centrum",
        "lat": 52.23,
        "lon": 21.0,
    }


def test_when_listing_vehicles_of_a_line_then_only_its_vehicles_are_returned(
    client: TestClient,
) -> None:
    response = client.get("/lines/1/175/vehicles")

    assert response.status_code == 200
    assert [vehicle["id"] for vehicle in response.json()] == ["1:2001"]


def test_when_listing_vehicles_of_an_unknown_line_then_empty_list_is_returned(
    client: TestClient,
) -> None:
    response = client.get("/lines/1/999/vehicles")

    assert response.status_code == 200
    assert response.json() == []


def test_when_getting_a_vehicle_then_its_view_is_returned(client: TestClient) -> None:
    response = client.get("/vehicles/2:3001")

    assert response.status_code == 200
    assert response.json()["line"] == "9"
    assert response.json()["next_stop"] == "Rondo Daszyńskiego"


def test_when_getting_an_unknown_vehicle_then_404(client: TestClient) -> None:
    response = client.get("/vehicles/9:9999")

    assert response.status_code == 404
