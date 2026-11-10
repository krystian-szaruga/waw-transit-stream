from fastapi.testclient import TestClient


def test_when_listing_trip_stops_then_they_are_returned_in_sequence_order(
    client: TestClient,
) -> None:
    response = client.get("/trips/t1/stops?date=2026-11-10")

    assert response.status_code == 200
    assert response.json() == [
        {
            "sequence": 1,
            "name": "Plac Zawiszy",
            "scheduled": "2026-11-10T00:00:00+01:00",
            "lat": 52.2301,
            "lon": 20.9901,
        },
        {
            "sequence": 2,
            "name": "Centrum",
            "scheduled": "2026-11-10T00:02:00+01:00",
            "lat": 52.2310,
            "lon": 20.9910,
        },
    ]


def test_when_listing_stops_of_an_unknown_trip_then_404(client: TestClient) -> None:
    response = client.get("/trips/unknown/stops?date=2026-11-10")

    assert response.status_code == 404


def test_when_listing_a_trip_shape_then_its_points_follow_the_road_geometry(
    client: TestClient,
) -> None:
    response = client.get("/trips/t1/shape")

    assert response.status_code == 200
    assert response.json() == [
        {"sequence": 0, "lat": 52.2300, "lon": 20.9900},
        {"sequence": 1, "lat": 52.2310, "lon": 20.9910},
    ]


def test_when_listing_a_shape_of_a_trip_without_geometry_then_empty_list(
    client: TestClient,
) -> None:
    response = client.get("/trips/unknown/shape")

    assert response.status_code == 200
    assert response.json() == []
