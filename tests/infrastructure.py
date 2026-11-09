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
                for statement in SCHEMA_STATEMENTS:
                    cur.execute(statement)
                cur.executemany(
                    "INSERT INTO gtfs_versions (version_id, sha256, status) VALUES (%s, %s, %s)",
                    VERSION_ROWS,
                )
                cur.executemany(
                    "INSERT INTO static_timetable VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    STOP_ROWS,
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
        client.hset("vehicle:1:2001", mapping=VEHICLE_2001)
        client.hset("vehicle:2:3001", mapping=VEHICLE_3001)
        client.sadd("line:1:175", "1:2001")
        client.sadd("line:2:9", "2:3001")
        client.zadd(
            "stop:1002",
            {
                json.dumps(DEPARTURE_MEMBER): PREDICTED.timestamp(),
                "not-json": PREDICTED.timestamp() + 1,
            },
        )
        yield


TZ = ZoneInfo("Europe/Warsaw")
API_TIMESTAMP = datetime(2026, 11, 10, 12, 0, tzinfo=TZ)
SCHEDULED = datetime(2026, 11, 10, 12, 5, tzinfo=TZ)
PREDICTED = datetime(2026, 11, 10, 12, 7, tzinfo=TZ)

SCHEMA_STATEMENTS = (
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

VERSION_ROWS = (
    (1, "a" * 64, "retired"),
    (2, "b" * 64, "active"),
)

STOP_ROWS = (
    (2, date(2026, 11, 10), 1, "175", "3", "r1", "t1", "1001", "Plac Zawiszy", 1, 52.2301, 20.9901, 0),
    (2, date(2026, 11, 10), 1, "175", "3", "r1", "t1", "1002", "Centrum", 2, 52.2310, 20.9910, 120),
    (2, date(2026, 11, 10), 2, "9", "1", "r2", "t2", "2001", "Rondo Daszyńskiego", 1, 52.2400, 21.0300, 60),
    (2, date(2026, 11, 10), 2, "9", "1", "r2", "t2", "2002", "Zajezdnia Wola", 2, 52.2500, 21.0400, 180),
    (1, date(2026, 11, 10), 1, "175", "3", "r1", "t1", "9999", "Old Stop", 1, 52.0, 21.0, 0),
)

VEHICLE_2001 = {
    "lat": "52.23",
    "lon": "21.0",
    "line": "175",
    "brigade": "3",
    "trip_id": "t1",
    "delay_sec": "45.5",
    "match_status": "MATCHED",
    "api_timestamp": API_TIMESTAMP.isoformat(),
    "gtfs_version": "2",
    "next_stop_sequence": "2",
    "next_stop": "Centrum",
}

VEHICLE_3001 = {
    "lat": "52.24",
    "lon": "21.03",
    "line": "9",
    "brigade": "1",
    "trip_id": "t2",
    "delay_sec": "-20.0",
    "match_status": "MATCHED",
    "api_timestamp": API_TIMESTAMP.isoformat(),
    "gtfs_version": "2",
    "next_stop_sequence": "1",
    "next_stop": "Rondo Daszyńskiego",
}

DEPARTURE_MEMBER = {
    "vehicle_id": "1:2001",
    "vehicle_type": 1,
    "line": "175",
    "brigade": "3",
    "trip_id": "t1",
    "stop_sequence": 2,
    "scheduled": SCHEDULED.isoformat(),
}
