from __future__ import annotations

import json
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
from confluent_kafka import Producer

from waw_transit_pipeline.adapters.kafka import stream_options, topic_to_vehicle_type
from waw_transit_pipeline.adapters.spark import open_stream, parse_records
from waw_transit_pipeline.processing.assignment import AssignmentPipeline
from waw_transit_pipeline.processing.model import WarsawLiveCol, LookupSnapshot
from waw_transit.database.redis.session import RedisSession
from waw_transit.database.redis import create_live_state_repository
from waw_transit_pipeline.processing.sink import LiveStatePreparer

_TIMEZONE = "Europe/Warsaw"
_TRIP_ID = "t2"
_VEHICLE_NUMBER = "3001"
_LINE = "9"
_GTFS_VERSION = 7


def _timetable(now: datetime) -> pd.DataFrame:
    midnight = datetime.combine(now.date(), time.min, tzinfo=ZoneInfo(_TIMEZONE))
    seconds = (now - midnight).total_seconds()
    return pd.DataFrame(
        {
            "service_date": [now.date(), now.date()],
            "vehicle_type": [2, 2],
            "line": [_LINE, _LINE],
            "brigade": ["3", "3"],
            "route_id": ["r2", "r2"],
            "trip_id": [_TRIP_ID, _TRIP_ID],
            "stop_id": ["2001", "2002"],
            "stop_name": ["Most", "Rondo"],
            "stop_sequence": [1, 2],
            "stop_lat": [52.25, 52.25],
            "stop_lon": [21.02, 21.03],
            "scheduled_arrival_offset": [seconds - 300, seconds + 300],
        }
    )


def _produce(bootstrap: str, topic: str, payload: dict) -> None:
    producer = Producer({"bootstrap.servers": bootstrap})
    producer.produce(topic, json.dumps(payload).encode())
    producer.flush()


def test_when_a_ping_arrives_on_kafka_then_it_reaches_redis(
    spark,
    redpanda,
    redis_config,
    load_lookup,
    tmp_path,
) -> None:
    now = datetime.now(ZoneInfo(_TIMEZONE)).replace(microsecond=0)
    lookup = load_lookup(_timetable(now)).lookup

    _produce(
        redpanda.bootstrap_servers,
        redpanda.topics["tram"],
        {
            WarsawLiveCol.LINE.value: _LINE,
            WarsawLiveCol.BRIGADE.value: "3",
            WarsawLiveCol.VEHICLE_NUMBER.value: _VEHICLE_NUMBER,
            WarsawLiveCol.LON.value: 21.025,
            WarsawLiveCol.LAT.value: 52.25,
            WarsawLiveCol.TIME.value: now.strftime("%Y-%m-%d %H:%M:%S"),
        },
    )

    broadcast = spark.sparkContext.broadcast(LookupSnapshot(lookup, _GTFS_VERSION))
    live = parse_records(
        open_stream("kafka", stream_options(redpanda)),
        value_column="value",
        topic_column="topic",
        topic_to_type=topic_to_vehicle_type(redpanda),
    ).read(spark)
    matched = AssignmentPipeline(broadcast).build(live)

    with RedisSession() as session:
        with session.open() as client:
            client.flushdb()

        repository = create_live_state_repository(session, _TIMEZONE)
        preparer = LiveStatePreparer(lookup, _TIMEZONE)
        query = (
            matched.writeStream.foreachBatch(
                lambda batch, _: repository.save(preparer.prepare(batch))
            )
            .option("checkpointLocation", str(tmp_path / "checkpoints"))
            .trigger(availableNow=True)
            .start()
        )
        query.awaitTermination(timeout=120)

        with session.open() as client:
            fields = client.hgetall(f"vehicle:2:{_VEHICLE_NUMBER}")

    broadcast.destroy()

    assert fields["trip_id"] == _TRIP_ID
    assert fields["line"] == _LINE
    assert fields["gtfs_version"] == str(_GTFS_VERSION)
