from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import redis.asyncio as aioredis

from waw_transit.config.env_reader import EnvReader
from waw_transit.core import VehicleSnapshot
from waw_transit.database.postgres.repository.stop_reader import (
    create_all_stops_reader,
    create_stop_reader,
)
from waw_transit.database.postgres.repository.trip_reader import create_lines_reader, create_trip_reader
from waw_transit.database.redis.departure_reader import create_stop_departures_reader
from waw_transit.database.redis.vehicle_reader import (
    create_all_vehicles_reader,
    create_line_vehicles_reader,
    create_vehicle_reader,
)
from waw_transit_backend.application.ports import Clock, LiveVehicleStream
from waw_transit_backend.application.services import (
    DepartureService,
    LineService,
    LiveFeedService,
    StopService,
    VehicleService,
)


@dataclass(frozen=True, slots=True)
class AppContainer:
    vehicle_service: VehicleService
    stop_service: StopService
    departure_service: DepartureService
    line_service: LineService
    live_feed_service: LiveFeedService


def create_container() -> AppContainer:
    vehicle_service = VehicleService(
        create_all_vehicles_reader(),
        create_line_vehicles_reader(),
        create_vehicle_reader(),
        create_trip_reader(),
    )
    departure_service = DepartureService(
        create_stop_departures_reader(),
        create_stop_reader(),
        create_trip_reader(),
        _SystemClock(),
    )
    return AppContainer(
        vehicle_service=vehicle_service,
        stop_service=StopService(create_all_stops_reader(), create_stop_reader()),
        departure_service=departure_service,
        line_service=LineService(create_lines_reader()),
        live_feed_service=LiveFeedService(
            vehicle_service,
            departure_service,
            _RedisLiveVehicleStream(),
        ),
    )


class _SystemClock(Clock):

    def now(self) -> datetime:
        return datetime.now(ZoneInfo("Europe/Warsaw"))


class _RedisLiveVehicleStream(LiveVehicleStream):
    _CHANNEL = "vehicles.updates"

    def __init__(self) -> None:
        env = EnvReader()
        self._client = aioredis.Redis(
            host=env.get("REDIS_HOST", "127.0.0.1"),
            port=env.get_int("REDIS_PORT", 6379),
            password=env.get("REDIS_PASSWORD", ""),
            db=env.get_int("REDIS_DB", 0),
            decode_responses=True,
        )

    async def stream(self) -> AsyncIterator[VehicleSnapshot]:
        pubsub = self._client.pubsub()
        await pubsub.subscribe(self._CHANNEL)
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                snapshot = _parse_update(str(message.get("data")))
                if snapshot is not None:
                    yield snapshot
        finally:
            await pubsub.aclose()


def _parse_update(raw: str) -> VehicleSnapshot | None:
    try:
        data = json.loads(raw)
        vehicle_type, vehicle_number = str(data["vehicle_id"]).split(":", 1)
        return VehicleSnapshot(
            vehicle_type=int(vehicle_type),
            vehicle_number=vehicle_number,
            line=str(data["line"]),
            brigade=str(data["brigade"]),
            trip_id=str(data["trip_id"]),
            delay=float(data["delay_sec"]),
            next_sequence=int(data["next_stop_sequence"]),
            gtfs_version=int(data["gtfs_version"]),
            timestamp=datetime.fromisoformat(data["api_timestamp"]),
            lat=float(data["lat"]),
            lon=float(data["lon"]),
            match_status=str(data["match_status"]),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
