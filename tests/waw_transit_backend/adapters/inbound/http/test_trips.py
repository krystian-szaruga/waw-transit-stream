from fastapi.testclient import TestClient


def test_when_listing_trip_stops_then_they_are_returned_in_sequence_order(
    client: TestClient,
) -> None:
    response = client.get("/trips/t1/stops?date=2026-11-10")

    assert response.status_code == 200
    assert response.json() == [
        {"sequence": 1, "name": "Plac Zawiszy", "scheduled": "2026-11-10T00:00:00+01:00"},
        {"sequence": 2, "name": "Centrum", "scheduled": "2026-11-10T00:02:00+01:00"},
    ]


def test_when_listing_stops_of_an_unknown_trip_then_404(client: TestClient) -> None:
    response = client.get("/trips/unknown/stops?date=2026-11-10")

    assert response.status_code == 404
