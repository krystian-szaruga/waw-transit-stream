from __future__ import annotations

import json
import logging
from collections.abc import ValuesView
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import pyspark.sql.functions as F
import redis
from pyspark.sql import DataFrame

from waw_transit_pipeline.processing.assignment.records import TripId, VehicleKey
from waw_transit_pipeline.processing.model import Lookup, MatchStatus, TripMatchCol
from waw_transit.database.redis import RedisSession

from .schedule import TripSchedule
from .vehicle import VehicleUpdate, VehicleValidation

logger = logging.getLogger("warsaw_transit_stream_processing")


class RedisSink:
    def __init__(self, session: RedisSession, lookup: Lookup, timezone: str) -> None:
        self._tz = ZoneInfo(timezone)
        self._session = session
        self._validation = VehicleValidation(timezone)
        self._schedules: dict[TripId, TripSchedule] = {
            TripId(trip.trip_id): TripSchedule(trip, self._tz) for trip in lookup
        }

    def write(self, batch_df: DataFrame) -> None:
        if not (vehicles := _Batch(batch_df, self._validation).latest_vehicles()):
            return
        try:
            with self._session.open() as client:
                pipe = client.pipeline(transaction=False)
                writer = _VehicleWriter(self._tz)
                for vehicle in vehicles:
                    writer.write(pipe, vehicle, self._schedule(vehicle.trip_id))
                writer.cleanup(pipe)
                pipe.execute()
        except redis.RedisError as err:
            logger.exception(f"Failed to write the batch to Redis, reason: {err}")

    def _schedule(self, trip_id: TripId) -> TripSchedule | None:
        return self._schedules.get(trip_id)


@dataclass(frozen=True, slots=True)
class _Batch:
    _frame: DataFrame
    _validation: VehicleValidation

    def latest_vehicles(self) -> ValuesView[VehicleUpdate]:
        status = TripMatchCol.MATCH_STATUS.value
        latest: dict[VehicleKey, VehicleUpdate] = {}
        rejected = 0
        for row in self._frame.where(F.col(status) == MatchStatus.MATCHED.value).collect():
            update = self._validation.validate(row)
            if update is None:
                rejected += 1
                continue
            held = latest.get(update.key)
            if held is None or update.is_newer_than(held):
                latest[update.key] = update
        if rejected:
            logger.warning("Rejected %d invalid vehicle rows in batch", rejected)
        return latest.values()


class _VehicleWriter:
    """Builds Redis pipeline commands for one batch.

    Holds per-batch state (`_touched_stops`), so create a new instance per batch.
    """

    _TTL_SEC = 180
    _STALE_GRACE_SEC = 60
    _CHANNEL = "vehicles.updates"

    def __init__(self, tz: ZoneInfo) -> None:
        self._tz = tz
        self._touched_stops: set[str] = set()

    def write(
        self,
        pipe: redis.client.Pipeline,
        update: VehicleUpdate,
        schedule: TripSchedule | None,
    ) -> None:
        self._hset(pipe, update)
        self._sadd(pipe, update)
        self._publish(pipe, update)
        if schedule is not None:
            self._departures(pipe, update, schedule)

    def cleanup(self, pipe: redis.client.Pipeline) -> None:
        cutoff = datetime.now(self._tz).timestamp() - self._STALE_GRACE_SEC
        for key in self._touched_stops:
            pipe.zremrangebyscore(key, "-inf", cutoff)
            pipe.expire(key, self._TTL_SEC)

    def _hset(self, pipe: redis.client.Pipeline, update: VehicleUpdate) -> None:
        key = self._vehicle_key(update)
        pipe.hset(key, mapping=self._fields(update))
        pipe.expire(key, self._TTL_SEC)

    def _sadd(self, pipe: redis.client.Pipeline, update: VehicleUpdate) -> None:
        key = self._line_key(update)
        pipe.sadd(key, self._vehicle_id(update))
        pipe.expire(key, self._TTL_SEC)

    def _publish(self, pipe: redis.client.Pipeline, update: VehicleUpdate) -> None:
        payload = {"vehicle_id": self._vehicle_id(update), **self._fields(update)}
        pipe.publish(self._CHANNEL, json.dumps(payload))

    def _departures(
        self,
        pipe: redis.client.Pipeline,
        update: VehicleUpdate,
        schedule: TripSchedule,
    ) -> None:
        for departure in schedule.departures(update.delay, update.next_sequence):
            key = f"stop:{departure.stop_id}"
            member = self._member(update, departure.stop_sequence, departure.scheduled)
            pipe.zadd(key, {member: departure.score})
            self._touched_stops.add(key)

    @staticmethod
    def _vehicle_id(update: VehicleUpdate) -> str:
        return f"{update.vehicle_type}:{update.vehicle_number}"

    @classmethod
    def _vehicle_key(cls, update: VehicleUpdate) -> str:
        return f"vehicle:{cls._vehicle_id(update)}"

    @staticmethod
    def _line_key(update: VehicleUpdate) -> str:
        return f"line:{update.vehicle_type}:{update.line}"

    @staticmethod
    def _fields(update: VehicleUpdate) -> dict[str, str]:
        return {
            "lat": str(update.lat),
            "lon": str(update.lon),
            "line": update.line,
            "brigade": update.brigade,
            "trip_id": update.trip_id,
            "delay_sec": str(update.delay),
            "match_status": update.match_status,
            "api_timestamp": update.timestamp.isoformat(),
            "gtfs_version": str(update.gtfs_version),
            "next_stop_sequence": str(update.next_sequence),
        }

    @classmethod
    def _member(cls, update: VehicleUpdate, stop_sequence: int, scheduled: datetime) -> str:
        return json.dumps({
            "vehicle_id": cls._vehicle_id(update),
            "vehicle_type": update.vehicle_type,
            "line": update.line,
            "brigade": update.brigade,
            "trip_id": update.trip_id,
            "stop_sequence": stop_sequence,
            "scheduled": scheduled.isoformat(),
        })