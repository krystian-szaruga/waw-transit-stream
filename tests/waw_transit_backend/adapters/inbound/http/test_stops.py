from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from waw_transit_backend.composition.app import create_app


def test_when_listing_stops_then_active_version_stops_are_returned_in_name_order(
    client: TestClient,
) -> None:
    response = client.get("/stops")

    assert response.status_code == 200
    assert [stop["id"] for stop in response.json()] == ["1002", "1001", "2001", "2002"]


def test_when_listing_stops_then_every_stop_has_its_full_details(client: TestClient) -> None:
    response = client.get("/stops")

    centrum = next(stop for stop in response.json() if stop["id"] == "1002")
    assert centrum == {"id": "1002", "name": "Centrum", "lat": 52.231, "lon": 20.991}


@pytest.mark.parametrize(
    ("query", "expected_ids"),
    [
        ("centrum", ["1002"]),
        ("ZAJEZDNIA", ["2002"]),
        ("plac zaw", ["1001"]),
    ],
)
def test_when_searching_stops_then_matching_is_case_insensitive_and_partial(
    client: TestClient,
    query: str,
    expected_ids: list[str],
) -> None:
    response = client.get("/stops", params={"query": query})

    assert response.status_code == 200
    assert [stop["id"] for stop in response.json()] == expected_ids


def test_when_searching_stops_without_matches_then_empty_list_is_returned(
    client: TestClient,
) -> None:
    response = client.get("/stops", params={"query": "kosmos"})

    assert response.status_code == 200
    assert response.json() == []


def test_when_getting_a_stop_then_its_details_are_returned(client: TestClient) -> None:
    response = client.get("/stops/1001")

    assert response.status_code == 200
    assert response.json() == {
        "id": "1001",
        "name": "Plac Zawiszy",
        "lat": 52.2301,
        "lon": 20.9901,
    }


@pytest.mark.parametrize("stop_id", ["9999", "does-not-exist"])
def test_when_getting_a_stop_outside_the_active_version_then_404(
    client: TestClient,
    stop_id: str,
) -> None:
    response = client.get(f"/stops/{stop_id}")

    assert response.status_code == 404


@pytest.fixture
def unreachable_database_client(
    monkeypatch: pytest.MonkeyPatch,
    postgres: None,
    redis_store: None,
) -> Iterator[TestClient]:
    monkeypatch.setenv("DB_PORT", "1")
    app: FastAPI = create_app()
    with TestClient(app) as client:
        yield client


def test_when_the_timetable_database_is_unreachable_then_503(
    unreachable_database_client: TestClient,
) -> None:
    response = unreachable_database_client.get("/stops")

    assert response.status_code == 503
