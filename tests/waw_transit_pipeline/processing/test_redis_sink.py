from __future__ import annotations

import json
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from waw_transit_pipeline.processing.assignment.schema import Schema
from waw_transit_pipeline.processing.model import TripMatchCol, MatchStatus
from waw_transit.database.redis import RedisSession
from waw_transit.database.redis.live_state_repository import RedisLiveStateRepository
from waw_transit_pipeline.processing.sink import LiveStatePreparer

_TIMEZONE = "Europe/Warsaw"
_CHANNEL = "vehicles.updates"


def _write(session, lookup, frame) -> None:
    RedisLiveStateRepository(session, _TIMEZONE).save(
        LiveStatePreparer(lookup, _TIMEZONE).prepare(frame)
    )


def _row(**overrides) -> dict[str, object]:
    values: dict[str, object] = {
        TripMatchCol.VEHICLE_TYPE.value: 1,
        TripMatchCol.VEHICLE_NUMBER.value: "2001",
        TripMatchCol.BRIGADE.value: "3",
        TripMatchCol.LINE.value: "175",
        TripMatchCol.TRIP_ID.value: "t1",
        TripMatchCol.DIST_M.value: 0.0,
        TripMatchCol.DELAY_SEC.value: 0.0,
        TripMatchCol.COST.value: 0.0,
        TripMatchCol.MATCH_STATUS.value: MatchStatus.MATCHED.value,
        TripMatchCol.API_TS.value: datetime.now(ZoneInfo(_TIMEZONE)),
        TripMatchCol.GTFS_VERSION.value: 7,
        TripMatchCol.LON.value: 21.0,
        TripMatchCol.LAT.value: 52.23,
        TripMatchCol.NEXT_STOP_SEQUENCE.value: 1,
    }
    values.update(overrides)
    return values


def _frame(spark, *rows):
    return spark.createDataFrame(list(rows), schema=Schema.output())


def _today_frame(now: datetime) -> pd.DataFrame:
    midnight = datetime.combine(now.date(), time.min, tzinfo=ZoneInfo(_TIMEZONE))
    seconds = (now - midnight).total_seconds()
    return pd.DataFrame(
        {
            "service_date": [now.date(), now.date()],
            "vehicle_type": [1, 1],
            "line": ["175", "175"],
            "brigade": ["3", "3"],
            "route_id": ["r1", "r1"],
            "trip_id": ["t1", "t1"],
            "stop_id": ["1001", "1002"],
            "stop_name": ["Start", "End"],
            "stop_sequence": [1, 2],
            "stop_lat": [52.23, 52.23],
            "stop_lon": [21.0, 21.006],
            "scheduled_arrival_offset": [seconds - 300, seconds + 300],
        }
    )


def test_when_a_matched_row_is_written_then_the_vehicle_hash_is_stored(
    spark,
    redis_config,
    load_lookup,
    timetable_frame,
) -> None:
    lookup = load_lookup(timetable_frame).lookup

    with RedisSession() as session:
        with session.open() as client:
            client.flushdb()
        _write(session, lookup, _frame(spark, _row()))
        with session.open() as client:
            fields = client.hgetall("vehicle:1:2001")
            ttl = client.ttl("vehicle:1:2001")

    assert fields["trip_id"] == "t1"
    assert fields["line"] == "175"
    assert fields["brigade"] == "3"
    assert fields["match_status"] == MatchStatus.MATCHED.value
    assert 0 < ttl <= 180


def test_when_a_matched_row_is_written_then_the_line_set_and_payload_are_published(
    spark,
    redis_config,
    load_lookup,
    timetable_frame,
) -> None:
    lookup = load_lookup(timetable_frame).lookup

    with RedisSession() as session:
        with session.open() as client:
            client.flushdb()
            pubsub = client.pubsub()
            pubsub.subscribe(_CHANNEL)
            pubsub.get_message(timeout=1.0)

            _write(session, lookup, _frame(spark, _row()))

            members = client.smembers("line:1:175")
            message = pubsub.get_message(timeout=5.0)
            pubsub.close()

    payload = json.loads(message["data"])

    assert members == {"1:2001"}
    assert payload["vehicle_id"] == "1:2001"
    assert payload["trip_id"] == "t1"
    assert payload["line"] == "175"


def test_when_a_scheduled_vehicle_is_written_then_stop_members_carry_the_predicted_time(
    spark,
    redis_config,
    load_lookup,
) -> None:
    now = datetime.now(ZoneInfo(_TIMEZONE))
    midnight = datetime.combine(now.date(), time.min, tzinfo=ZoneInfo(_TIMEZONE))
    lookup = load_lookup(_today_frame(now)).lookup
    scheduled = midnight + timedelta(seconds=(now - midnight).total_seconds() + 300)

    with RedisSession() as session:
        with session.open() as client:
            client.flushdb()
        _write(session, lookup, _frame(spark, _row()))
        with session.open() as client:
            entries = client.zrange("stop:1002", 0, -1, withscores=True)

    assert len(entries) == 1
    member, score = entries[0]
    payload = json.loads(member)

    assert payload["trip_id"] == "t1"
    assert payload["stop_sequence"] == 2
    assert payload["scheduled"] == scheduled.isoformat()
    assert score == pytest.approx(scheduled.timestamp())


def test_when_a_vehicle_pings_twice_then_only_the_newer_update_is_written(
    spark,
    redis_config,
    load_lookup,
    timetable_frame,
) -> None:
    lookup = load_lookup(timetable_frame).lookup
    newer = datetime.now(ZoneInfo(_TIMEZONE))
    older = newer - timedelta(seconds=30)

    with RedisSession() as session:
        with session.open() as client:
            client.flushdb()
        _write(session, lookup, _frame(
            spark,
            _row(**{TripMatchCol.API_TS.value: older, TripMatchCol.DELAY_SEC.value: 10.0}),
            _row(**{TripMatchCol.API_TS.value: newer, TripMatchCol.DELAY_SEC.value: 20.0}),
        ))
        with session.open() as client:
            fields = client.hgetall("vehicle:1:2001")

    assert fields["delay_sec"] == "20.0"


def test_when_a_row_is_invalid_then_nothing_is_written_for_it(
    spark,
    redis_config,
    load_lookup,
    timetable_frame,
) -> None:
    lookup = load_lookup(timetable_frame).lookup
    stale = datetime.now(ZoneInfo(_TIMEZONE)) - timedelta(minutes=10)

    with RedisSession() as session:
        with session.open() as client:
            client.flushdb()
        _write(session, lookup, _frame(
            spark,
            _row(**{TripMatchCol.LINE.value: None}),
            _row(**{TripMatchCol.API_TS.value: stale, TripMatchCol.VEHICLE_NUMBER.value: "2002"}),
        ))
        with session.open() as client:
            keys = client.keys("*")

    assert keys == []


def test_when_a_row_is_unmatched_then_it_is_not_written(
    spark,
    redis_config,
    load_lookup,
    timetable_frame,
) -> None:
    lookup = load_lookup(timetable_frame).lookup

    with RedisSession() as session:
        with session.open() as client:
            client.flushdb()
        _write(session, lookup, _frame(
            spark,
            _row(**{TripMatchCol.MATCH_STATUS.value: MatchStatus.UNMATCHED.value}),
        ))
        with session.open() as client:
            keys = client.keys("*")

    assert keys == []


def test_when_a_stop_holds_stale_members_then_cleanup_drops_them(
    spark,
    redis_config,
    load_lookup,
) -> None:
    now = datetime.now(ZoneInfo(_TIMEZONE))
    lookup = load_lookup(_today_frame(now)).lookup
    stale_score = (now - timedelta(hours=1)).timestamp()

    with RedisSession() as session:
        with session.open() as client:
            client.flushdb()
            client.zadd("stop:1002", {"old": stale_score})
        _write(session, lookup, _frame(
            spark,
            _row(**{TripMatchCol.NEXT_STOP_SEQUENCE.value: 2}),
        ))
        with session.open() as client:
            members = client.zrange("stop:1002", 0, -1)
            ttl = client.ttl("stop:1002")

    assert "old" not in members
    assert len(members) == 1
    assert 0 < ttl <= 180
