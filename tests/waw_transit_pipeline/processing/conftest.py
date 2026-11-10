import os
from collections.abc import Iterator
from datetime import date

import pandas as pd
import pytest
from confluent_kafka.admin import AdminClient, NewTopic
from pyspark.sql import SparkSession
from testcontainers.community.kafka import RedpandaContainer
from testcontainers.community.redis import RedisContainer

from waw_transit_pipeline.core.config import KafkaConfig
from waw_transit.core import ReadRepository
from waw_transit_pipeline.processing.lookup import LookupLoader
from waw_transit_pipeline.processing.model import VehicleType


class _FrameRepository(ReadRepository):
    def __init__(self, frame: pd.DataFrame, version_id: int = 7) -> None:
        self._frame = frame
        self._version_id = version_id

    def load(self, payload=None) -> tuple[pd.DataFrame, int]:
        return self._frame, self._version_id


@pytest.fixture(scope="session")
def redpanda() -> Iterator[KafkaConfig]:
    topics = {VehicleType.BUS: "buses", VehicleType.TRAM: "trams"}
    with RedpandaContainer("redpandadata/redpanda:v23.1.13") as container:
        bootstrap = container.get_bootstrap_server()
        admin = AdminClient({"bootstrap.servers": bootstrap})
        created = admin.create_topics(
            [NewTopic(name, num_partitions=1, replication_factor=1) for name in [*topics.values(), "versions"]]
        )
        for future in created.values():
            future.result()
        yield KafkaConfig(
            bootstrap_servers=bootstrap,
            client_id="tests",
            starting_offsets="earliest",
            topics={VehicleType.BUS.name.lower(): "buses", VehicleType.TRAM.name.lower(): "trams"},
            version_topic="versions",
        )


@pytest.fixture(scope="session")
def redis_config() -> Iterator[None]:
    with RedisContainer("redis:7-alpine") as container:
        os.environ["REDIS_HOST"] = container.get_container_host_ip()
        os.environ["REDIS_PORT"] = str(container.get_exposed_port(6379))
        os.environ["REDIS_PASSWORD"] = ""
        os.environ["REDIS_DB"] = "0"
        yield


@pytest.fixture(scope="session")
def spark() -> Iterator[SparkSession]:
    session: SparkSession = (
        SparkSession.builder.master("local[1]")
        .appName("waw-transit-stream-tests")
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.13:4.3.0")
        .config("spark.sql.session.timeZone", "Europe/Warsaw")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("WARN")
    yield session
    session.stop()


@pytest.fixture
def load_lookup():
    def _load(frame: pd.DataFrame, version_id: int = 7):
        return LookupLoader(_FrameRepository(frame, version_id)).load()

    return _load


@pytest.fixture
def timetable_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "service_date": [date(2026, 11, 4)] * 4,
            "vehicle_type": [1, 1, 2, 2],
            "line": ["175", "175", "9", "9"],
            "brigade": ["1", "1", "3", "3"],
            "route_id": ["r1", "r1", "r2", "r2"],
            "trip_id": ["t1", "t1", "t2", "t2"],
            "stop_id": ["1001", "1002", "2001", "2002"],
            "stop_name": ["Start", "End", "Most", "Rondo"],
            "stop_sequence": [1, 2, 1, 2],
            "stop_lat": [52.23, 52.23, 52.25, 52.25],
            "stop_lon": [21.0, 21.006, 21.02, 21.03],
            "scheduled_arrival_offset": [86400, 88000, 28800, 29400],
        }
    )
