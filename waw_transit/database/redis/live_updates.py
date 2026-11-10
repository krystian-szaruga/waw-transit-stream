from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime

import redis.asyncio as aioredis

from waw_transit.config.env_reader import EnvReader
from waw_transit.core import LiveVehicleStream, VehicleSnapshot


def create_live_vehicle_stream() -> LiveVehicleStream:
    env = EnvReader()
    client = aioredis.Redis(
        host=env.get("REDIS_HOST", "127.0.0.1"),
        port=env.get_int("REDIS_PORT", 6379),
        password=env.get("REDIS_PASSWORD", ""),
        db=env.get_int("REDIS_DB", 0),
        decode_responses=True,
    )
    return _RedisLiveVehicleStream(client)


class _RedisLiveVehicleStream(LiveVehicleStream):
    _CHANNEL = "vehicles.updates"

    def __init__(self, client: aioredis.Redis) -> None:
        self._client = client

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
            next_stop=str(data.get("next_stop") or "") or None,
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
