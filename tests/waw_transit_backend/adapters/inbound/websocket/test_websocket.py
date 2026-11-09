from __future__ import annotations

import json
import os
import threading

import redis as redis_client
from fastapi.testclient import TestClient

VEHICLE_UPDATE = {
    "vehicle_id": "1:2001",
    "lat": "52.23",
    "lon": "21.0",
    "line": "175",
    "brigade": "3",
    "trip_id": "t1",
    "delay_sec": "45.5",
    "match_status": "MATCHED",
    "api_timestamp": "2026-11-10T12:00:00+01:00",
    "gtfs_version": "2",
    "next_stop_sequence": "2",
    "next_stop": "Centrum",
}


def test_when_subscribing_then_snapshot_with_all_live_vehicles_is_sent(
    client: TestClient,
) -> None:
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "subscribe"})

        message = websocket.receive_json()

    assert message["type"] == "snapshot"
    assert {vehicle["id"] for vehicle in message["vehicles"]} == {"1:2001", "2:3001"}
    assert message["departures"] == []


def test_when_subscribing_to_a_line_then_only_its_vehicles_are_sent(
    client: TestClient,
) -> None:
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "subscribe", "line": "9"})

        message = websocket.receive_json()

    assert [vehicle["id"] for vehicle in message["vehicles"]] == ["2:3001"]


def test_when_subscribing_to_a_stop_then_its_departures_are_sent(
    client: TestClient,
) -> None:
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "subscribe", "stop_id": "1002"})

        message = websocket.receive_json()

    assert [departure["stop_id"] for departure in message["departures"]] == ["1002"]


def test_when_a_vehicle_update_is_published_then_an_update_message_is_sent(
    client: TestClient,
) -> None:
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "subscribe"})
        assert websocket.receive_json()["type"] == "snapshot"

        published = threading.Event()
        publisher = threading.Thread(target=_publish_until, args=(published,))
        publisher.start()
        try:
            message = websocket.receive_json()
        finally:
            published.set()
            publisher.join(timeout=5)

    assert message["type"] == "update"
    assert {vehicle["id"] for vehicle in message["vehicles"]} == {"1:2001", "2:3001"}


def _publish_until(stop: threading.Event) -> None:
    client = redis_client.Redis(
        host=os.environ.get("REDIS_HOST", "127.0.0.1"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        password=os.environ.get("REDIS_PASSWORD", ""),
        db=int(os.environ.get("REDIS_DB", "0")),
        decode_responses=True,
    )
    try:
        while not stop.is_set():
            client.publish("vehicles.updates", json.dumps(VEHICLE_UPDATE))
            stop.wait(0.05)
    finally:
        client.close()
