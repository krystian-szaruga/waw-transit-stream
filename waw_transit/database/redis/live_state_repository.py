from __future__ import annotations

import json
import logging
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from typing import override
from zoneinfo import ZoneInfo

import redis

from waw_transit.core import ProviderSaveRepository, SaveRepository
from waw_transit.core.models import LiveStateBatch, StopDeparture, VehicleSnapshot
from waw_transit.database.redis.session import RedisSession

logger = logging.getLogger(__name__)


@contextmanager
def open_live_state_repository(timezone: str) -> Iterator[SaveRepository[LiveStateBatch, None]]:
    with RedisSession() as session:
        yield create_live_state_repository(session, timezone)


def create_live_state_repository(session: RedisSession, timezone: str) -> SaveRepository[LiveStateBatch, None]:
    return _RedisLiveStateRepository(session, timezone)


class _RedisLiveStateRepository(ProviderSaveRepository[redis.Redis, LiveStateBatch, None]):

    def __init__(self, session: RedisSession, timezone: str) -> None:
        super().__init__(session)
        self._timezone = ZoneInfo(timezone)

    @override
    def save(self, frame: LiveStateBatch) -> None:
        try:
            with self._provider.open() as client:
                pipe = client.pipeline(transaction=False)
                commands = _VehicleCommands(self._timezone)
                for vehicle in frame.vehicles:
                    commands.write(pipe, vehicle, frame.departures.get(vehicle.vehicle_id, ()))
                commands.cleanup(pipe)
                pipe.execute()
        except redis.RedisError as err:
            logger.exception(f"Failed to write the batch to Redis, reason: {err}")


class _VehicleCommands:
    _TTL_SEC = 180
    _STALE_GRACE_SEC = 60
    _CHANNEL = "vehicles.updates"

    def __init__(self, tz: ZoneInfo) -> None:
        self._tz = tz
        self._touched_stops: set[str] = set()

    def write(
        self,
        pipe: redis.client.Pipeline,
        vehicle: VehicleSnapshot,
        departures: Sequence[StopDeparture],
    ) -> None:
        self._hset(pipe, vehicle)
        self._sadd(pipe, vehicle)
        self._publish(pipe, vehicle)
        self._departures(pipe, vehicle, departures)

    def cleanup(self, pipe: redis.client.Pipeline) -> None:
        cutoff = datetime.now(self._tz).timestamp() - self._STALE_GRACE_SEC
        for key in self._touched_stops:
            pipe.zremrangebyscore(key, "-inf", cutoff)
            pipe.expire(key, self._TTL_SEC)

    def _hset(self, pipe: redis.client.Pipeline, vehicle: VehicleSnapshot) -> None:
        key = self._vehicle_key(vehicle)
        pipe.hset(key, mapping=self._fields(vehicle))
        pipe.expire(key, self._TTL_SEC)

    def _sadd(self, pipe: redis.client.Pipeline, vehicle: VehicleSnapshot) -> None:
        key = self._line_key(vehicle)
        pipe.sadd(key, vehicle.vehicle_id)
        pipe.expire(key, self._TTL_SEC)

    def _publish(self, pipe: redis.client.Pipeline, vehicle: VehicleSnapshot) -> None:
        payload = {"vehicle_id": vehicle.vehicle_id, **self._fields(vehicle)}
        pipe.publish(self._CHANNEL, json.dumps(payload))

    def _departures(
        self,
        pipe: redis.client.Pipeline,
        vehicle: VehicleSnapshot,
        departures: Sequence[StopDeparture],
    ) -> None:
        for departure in departures:
            key = self._stop_key(departure)
            member = self._member(vehicle, departure)
            pipe.zadd(key, {member: departure.score})
            self._touched_stops.add(key)

    @staticmethod
    def _vehicle_key(vehicle: VehicleSnapshot) -> str:
        return f"vehicle:{vehicle.vehicle_id}"

    @staticmethod
    def _line_key(vehicle: VehicleSnapshot) -> str:
        return f"line:{vehicle.vehicle_type}:{vehicle.line}"

    @staticmethod
    def _stop_key(departure: StopDeparture) -> str:
        return f"stop:{departure.stop_id}"

    @staticmethod
    def _fields(vehicle: VehicleSnapshot) -> dict[str, str]:
        return {
            "lat": str(vehicle.lat),
            "lon": str(vehicle.lon),
            "line": vehicle.line,
            "brigade": vehicle.brigade,
            "trip_id": vehicle.trip_id,
            "delay_sec": str(vehicle.delay),
            "match_status": vehicle.match_status,
            "api_timestamp": vehicle.timestamp.isoformat(),
            "gtfs_version": str(vehicle.gtfs_version),
            "next_stop_sequence": str(vehicle.next_sequence),
        }

    @staticmethod
    def _member(vehicle: VehicleSnapshot, departure: StopDeparture) -> str:
        return json.dumps({
            "vehicle_id": vehicle.vehicle_id,
            "vehicle_type": vehicle.vehicle_type,
            "line": vehicle.line,
            "brigade": vehicle.brigade,
            "trip_id": vehicle.trip_id,
            "stop_sequence": departure.stop_sequence,
            "scheduled": departure.scheduled.isoformat(),
        })
