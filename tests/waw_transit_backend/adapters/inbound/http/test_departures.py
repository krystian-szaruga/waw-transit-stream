from fastapi.testclient import TestClient


def test_when_listing_departures_then_schedule_and_vehicle_details_are_exposed(
    client: TestClient,
) -> None:
    response = client.get("/stops/1002/departures")

    assert response.status_code == 200
    departure = response.json()[0]
    assert departure["stop_id"] == "1002"
    assert departure["line"] == "175"
    assert departure["direction"] == "Centrum"
    assert departure["vehicle_id"] == "1:2001"
    assert departure["scheduled"] == "2026-11-10T12:05:00+01:00"
    assert departure["predicted"] == "2026-11-10T12:07:00+01:00"
    assert departure["delay_sec"] == 120.0
    assert isinstance(departure["minutes"], int)


def test_when_listing_departures_of_a_known_stop_without_them_then_empty_list_is_returned(
    client: TestClient,
) -> None:
    response = client.get("/stops/2002/departures")

    assert response.status_code == 200
    assert response.json() == []


def test_when_listing_departures_of_an_unknown_stop_then_404(client: TestClient) -> None:
    response = client.get("/stops/9999/departures")

    assert response.status_code == 404
