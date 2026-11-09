from __future__ import annotations

import json
import os
from collections.abc import Iterator
from datetime import date, datetime
from zoneinfo import ZoneInfo

import psycopg2
import pytest
import redis as redis_client
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.redis import RedisContainer

from waw_transit.core import VehicleSnapshot
from waw_transit.core.models.static_state import LineInfo, StopInfo, TripStop
from waw_transit.database.postgres.repository.stop_reader import (
    create_all_stops_reader,
    create_stop_reader,
)
from waw_transit.database.postgres.repository.trip_reader import (
    create_lines_reader,
    create_trip_reader,
)
from waw_transit.database.redis.departure_reader import create_stop_departures_reader
from waw_transit.database.redis.vehicle_reader import (
    create_all_vehicles_reader,
    create_line_vehicles_reader,
    create_vehicle_reader,
)


@pytest.fixture(scope="session")
def postgres() -> Iterator[None]:
    with PostgresContainer("postgres:16-alpine") as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)
        os.environ["DB_HOST"] = host
        os.environ["DB_PORT"] = str(port)
        os.environ["DB_NAME"] = container.dbname
        os.environ["DB_USER"] = container.username
        os.environ["DB_PASSWORD"] = container.password
        with psycopg2.connect(
            host=host,
            port=port,
            dbname=container.dbname,
            user=container.username,
            password=container.password,
        ) as connection:
            connection.autocommit = True
            with connection.cursor() as cur:
                for statement in _SCHEMA_STATEMENTS:
                    cur.execute(statement)
                cur.executemany(
                    "INSERT INTO gtfs_versions (version_id, sha256, status) VALUES (%s, %s, %s)",
                    _VERSION_ROWS,
                )
                cur.executemany(
                    "INSERT INTO static_timetable VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    _STOP_ROWS,
                )
        yield


@pytest.fixture(scope="session")
def redis_store() -> Iterator[None]:
    with RedisContainer("redis:7-alpine") as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(6379)
        os.environ["REDIS_HOST"] = host
        os.environ["REDIS_PORT"] = str(port)
        os.environ["REDIS_PASSWORD"] = ""
        os.environ["REDIS_DB"] = "0"
        client: redis_client.Redis = redis_client.Redis(
            host=host,
            port=port,
            decode_responses=True,
        )
        client.hset("vehicle:1:2001", mapping=_VEHICLE_2001)
        client.hset("vehicle:2:3001", mapping=_VEHICLE_3001)
        client.sadd("line:1:175", "1:2001")
        client.sadd("line:2:9", "2:3001")
        client.zadd(
            "stop:1002",
            {
                json.dumps(_DEPARTURE_MEMBER): _PREDICTED.timestamp(),
                "not-json": _PREDICTED.timestamp() + 1,
            },
        )
        yield


def test_when_reading_all_stops_then_only_stops_of_the_active_version_are_returned(
    postgres: None,
) -> None:
    stops = create_all_stops_reader().load()

    assert [stop.name for stop in stops] == [
        "Centrum",
        "Plac Zawiszy",
        "Rondo Daszyńskiego",
        "Zajezdnia Wola",
    ]
    assert all(stop.stop_id != "9999" for stop in stops)


def test_when_reading_a_stop_then_the_active_version_is_used(postgres: None) -> None:
    reader = create_stop_reader()

    assert reader.load("1002") == StopInfo("1002", "Centrum", 52.2310, 20.9910)
    assert reader.load("9999") is None


def test_when_reading_a_trip_then_stops_come_in_sequence_order(postgres: None) -> None:
    trip = create_trip_reader().load("t1")

    assert trip == (TripStop(1, "Plac Zawiszy"), TripStop(2, "Centrum"))


def test_when_reading_lines_then_distinct_lines_of_the_active_version_are_returned(
    postgres: None,
) -> None:
    lines = create_lines_reader().load()

    assert lines == (LineInfo("175", 1), LineInfo("9", 2))


def test_when_reading_all_vehicles_then_hashes_are_mapped_to_snapshots(
    redis_store: None,
) -> None:
    vehicles = create_all_vehicles_reader().load()

    assert {vehicle.vehicle_id for vehicle in vehicles} == {"1:2001", "2:3001"}


def test_when_reading_a_line_then_only_its_vehicles_are_returned(redis_store: None) -> None:
    vehicles = create_line_vehicles_reader().load((1, "175"))

    assert [vehicle.vehicle_id for vehicle in vehicles] == ["1:2001"]


def test_when_reading_a_vehicle_then_every_hash_field_is_mapped(redis_store: None) -> None:
    vehicle = create_vehicle_reader().load("1:2001")

    assert vehicle == VehicleSnapshot(
        vehicle_type=1,
        vehicle_number="2001",
        line="175",
        brigade="3",
        trip_id="t1",
        delay=45.5,
        next_sequence=2,
        gtfs_version=2,
        timestamp=_API_TIMESTAMP,
        lat=52.23,
        lon=21.0,
        match_status="MATCHED",
    )


def test_when_reading_an_unknown_vehicle_then_none_is_returned(redis_store: None) -> None:
    assert create_vehicle_reader().load("9:9999") is None


def test_when_reading_departures_then_valid_entries_are_parsed_and_bad_ones_skipped(
    redis_store: None,
) -> None:
    departures = create_stop_departures_reader().load("1002")

    assert len(departures) == 1
    assert departures[0].stop_id == "1002"
    assert departures[0].stop_sequence == 2
    assert departures[0].scheduled == _SCHEDULED
    assert departures[0].predicted == _PREDICTED


def test_when_reading_an_unknown_stop_then_departures_are_empty(redis_store: None) -> None:
    assert create_stop_departures_reader().load("9999") == ()


_TZ = ZoneInfo("Europe/Warsaw")
_API_TIMESTAMP = datetime(2026, 11, 10, 12, 0, tzinfo=_TZ)
_SCHEDULED = datetime(2026, 11, 10, 12, 5, tzinfo=_TZ)
_PREDICTED = datetime(2026, 11, 10, 12, 7, tzinfo=_TZ)

_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE gtfs_versions (
        version_id BIGSERIAL PRIMARY KEY,
        sha256 CHAR(64) NOT NULL UNIQUE,
        loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        status TEXT NOT NULL DEFAULT 'loading'
    )
    """,
    """
    CREATE TABLE static_timetable (
        gtfs_version BIGINT NOT NULL REFERENCES gtfs_versions(version_id),
        service_date DATE NOT NULL,
        vehicle_type SMALLINT NOT NULL,
        line VARCHAR(10) NOT NULL,
        brigade VARCHAR(10) NOT NULL,
        route_id VARCHAR(50) NOT NULL,
        trip_id VARCHAR(50) NOT NULL,
        stop_id VARCHAR(50) NOT NULL,
        stop_name VARCHAR(255),
        stop_sequence INT NOT NULL,
        stop_lat DOUBLE PRECISION NOT NULL,
        stop_lon DOUBLE PRECISION NOT NULL,
        scheduled_arrival_offset INT NOT NULL,
        PRIMARY KEY (gtfs_version, service_date, trip_id, stop_sequence)
    )
    """,
)

_VERSION_ROWS = (
    (1, "a" * 64, "retired"),
    (2, "b" * 64, "active"),
)

_STOP_ROWS = (
    (2, date(2026, 11, 10), 1, "175", "3", "r1", "t1", "1001", "Plac Zawiszy", 1, 52.2301, 20.9901, 0),
    (2, date(2026, 11, 10), 1, "175", "3", "r1", "t1", "1002", "Centrum", 2, 52.2310, 20.9910, 120),
    (2, date(2026, 11, 10), 2, "9", "1", "r2", "t2", "2001", "Rondo Daszyńskiego", 1, 52.2400, 21.0300, 60),
    (2, date(2026, 11, 10), 2, "9", "1", "r2", "t2", "2002", "Zajezdnia Wola", 2, 52.2500, 21.0400, 180),
    (1, date(2026, 11, 10), 1, "175", "3", "r1", "t1", "9999", "Old Stop", 1, 52.0, 21.0, 0),
)

_VEHICLE_2001 = {
    "lat": "52.23",
    "lon": "21.0",
    "line": "175",
    "brigade": "3",
    "trip_id": "t1",
    "delay_sec": "45.5",
    "match_status": "MATCHED",
    "api_timestamp": _API_TIMESTAMP.isoformat(),
    "gtfs_version": "2",
    "next_stop_sequence": "2",
}

_VEHICLE_3001 = {
    "lat": "52.24",
    "lon": "21.03",
    "line": "9",
    "brigade": "1",
    "trip_id": "t2",
    "delay_sec": "-20.0",
    "match_status": "MATCHED",
    "api_timestamp": _API_TIMESTAMP.isoformat(),
    "gtfs_version": "2",
    "next_stop_sequence": "1",
}

_DEPARTURE_MEMBER = {
    "vehicle_id": "1:2001",
    "vehicle_type": 1,
    "line": "175",
    "brigade": "3",
    "trip_id": "t1",
    "stop_sequence": 2,
    "scheduled": _SCHEDULED.isoformat(),
}
