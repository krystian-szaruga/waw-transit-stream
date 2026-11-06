from __future__ import annotations

import json
import logging
from collections.abc import Iterator, ValuesView
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pyspark.sql.functions as F
import redis
from pyspark.sql import DataFrame, Row

from processing.assignment.records import TripId, VehicleKey
from processing.model import Lookup, MatchStatus, Trip, TripMatchCol
from processing.session import RedisSession

logger = logging.getLogger("warsaw_transit_stream_processing")


class RedisSink:
    _TTL_SEC = 180
    _STALE_GRACE_SEC = 60
    _CHANNEL = "vehicles.updates"

    def __init__(self, session: RedisSession, lookup: Lookup, timezone: str) -> None:
        self._tz = ZoneInfo(timezone)
        self._session = session
        self._schedules: dict[TripId, _TripSchedule] = {
            TripId(trip.trip_id): _TripSchedule(trip, self._tz) for trip in lookup
        }

    def write(self, batch_df: DataFrame) -> None:
        if not (vehicles := _Batch(batch_df).latest_vehicles()): return
        try:
            with self._session.open() as client:
                pipe = client.pipeline(transaction=False)
                touched_stops: set[str] = set()
                for vehicle in vehicles:
                    vehicle.hset(pipe, self._TTL_SEC)
                    vehicle.sadd(pipe, self._TTL_SEC)
                    vehicle.publish(pipe, self._CHANNEL)
                    schedule = self._schedule(vehicle.trip_id)
                    if schedule is not None:
                        touched_stops.update(vehicle.departures(pipe, schedule))
                self._cleanup_stops(pipe, touched_stops)
                pipe.execute()
        except redis.RedisError as err:
            logger.exception(f"Failed to write the batch to Redis, reason: {err}")

    def _cleanup_stops(self, pipe: redis.client.Pipeline, stop_keys: set[str]) -> None:
        cutoff = datetime.now(self._tz).timestamp() - self._STALE_GRACE_SEC
        for key in stop_keys:
            pipe.zremrangebyscore(key, "-inf", cutoff)
            pipe.expire(key, self._TTL_SEC)

    def _schedule(self, trip_id: TripId) -> _TripSchedule | None:
        return self._schedules.get(trip_id)


@dataclass(frozen=True, slots=True)
class _Batch:
    _frame: DataFrame

    def latest_vehicles(self) -> ValuesView[_VehicleUpdate]:
        status = TripMatchCol.MATCH_STATUS.value
        latest: dict[VehicleKey, _VehicleUpdate] = {}
        for row in self._frame.where(F.col(status) != MatchStatus.UNMATCHED.value).collect():
            update = _VehicleUpdate.from_row(row)
            held = latest.get(update.key)
            if held is None or update.is_newer_than(held):
                latest[update.key] = update
        return latest.values()


@dataclass(frozen=True, slots=True)
class _VehicleUpdate:
    _vehicle_type: int
    _vehicle_number: str
    _line: str
    _brigade: str
    _trip_id: TripId
    _delay: float
    _next_sequence: int
    _gtfs_version: int
    _timestamp: datetime
    _lat: float
    _lon: float
    _match_status: str

    @classmethod
    def from_row(cls, row: Row) -> _VehicleUpdate:
        return cls(
            _vehicle_type=int(row[TripMatchCol.VEHICLE_TYPE.value]),
            _vehicle_number=str(row[TripMatchCol.VEHICLE_NUMBER.value]),
            _line=str(row[TripMatchCol.LINE.value]),
            _brigade=str(row[TripMatchCol.BRIGADE.value]),
            _trip_id=TripId(str(row[TripMatchCol.TRIP_ID.value])),
            _delay=float(row[TripMatchCol.DELAY_SEC.value]),
            _next_sequence=int(row[TripMatchCol.NEXT_STOP_SEQUENCE.value]),
            _gtfs_version=int(row[TripMatchCol.GTFS_VERSION.value]),
            _timestamp=row[TripMatchCol.API_TS.value],
            _lat=float(row[TripMatchCol.LAT.value]),
            _lon=float(row[TripMatchCol.LON.value]),
            _match_status=str(row[TripMatchCol.MATCH_STATUS.value]),
        )

    @property
    def trip_id(self) -> TripId:
        return self._trip_id

    @property
    def key(self) -> VehicleKey:
        return VehicleKey(self._vehicle_type, self._vehicle_number)

    @property
    def _vehicle_id(self) -> str:
        return f"{self._vehicle_type}:{self._vehicle_number}"

    @property
    def _vehicle_key(self) -> str:
        return f"vehicle:{self._vehicle_id}"

    @property
    def _line_key(self) -> str:
        return f"line:{self._vehicle_type}:{self._line}"

    @property
    def _fields(self) -> dict[str, str]:
        return {
            "lat": str(self._lat),
            "lon": str(self._lon),
            "line": self._line,
            "brigade": self._brigade,
            "trip_id": self._trip_id,
            "delay_sec": str(self._delay),
            "match_status": self._match_status,
            "api_timestamp": self._timestamp.isoformat(),
            "gtfs_version": str(self._gtfs_version),
            "next_stop_sequence": str(self._next_sequence),
        }

    def is_newer_than(self, other: _VehicleUpdate) -> bool:
        return self._timestamp > other._timestamp

    def hset(self, pipe: redis.client.Pipeline, ttl: int) -> None:
        pipe.hset(self._vehicle_key, mapping=self._fields)
        pipe.expire(self._vehicle_key, ttl)

    def sadd(self, pipe: redis.client.Pipeline, ttl: int) -> None:
        pipe.sadd(self._line_key, self._vehicle_id)
        pipe.expire(self._line_key, ttl)

    def publish(self, pipe: redis.client.Pipeline, channel: str) -> None:
        pipe.publish(channel, json.dumps({"vehicle_id": self._vehicle_id, **self._fields}))

    def departures(self, pipe: redis.client.Pipeline, schedule: _TripSchedule) -> list[str]:
        keys: list[str] = []
        for stop_id, score, stop_sequence, scheduled, _predicted in schedule.departures(
            self._delay, self._next_sequence
        ):
            key = f"stop:{stop_id}"
            pipe.zadd(key, {self._member(stop_sequence, scheduled): score})
            keys.append(key)
        return keys

    def _member(self, stop_sequence: int, scheduled: datetime) -> str:
        return json.dumps({
            "vehicle_id": self._vehicle_id,
            "vehicle_type": self._vehicle_type,
            "line": self._line,
            "brigade": self._brigade,
            "trip_id": self._trip_id,
            "stop_sequence": stop_sequence,
            "scheduled": scheduled.isoformat(),
        })


@dataclass(frozen=True, slots=True)
class _TripSchedule:
    _trip: Trip
    _tz: ZoneInfo
    _midnight: datetime = field(init=False, repr=False)

    def __post_init__(self) -> None:
        midnight = datetime.combine(self._trip.key.service_date, time.min, tzinfo=self._tz)
        object.__setattr__(self, "_midnight", midnight)

    def departures(
        self,
        delay: float,
        next_sequence: int,
    ) -> Iterator[tuple[str, float, int, datetime, datetime]]:
        for index in range(self._index(next_sequence), len(self._trip.seq)):
            scheduled = self._midnight + timedelta(seconds=float(self._trip.off[index]))
            predicted = scheduled + timedelta(seconds=delay)
            yield str(self._trip.stop_id[index]), predicted.timestamp(), int(self._trip.seq[index]), scheduled, predicted

    def _index(self, sequence: int) -> int:
        indices = np.flatnonzero(self._trip.seq == sequence)
        return int(indices[0]) if len(indices) else 0
