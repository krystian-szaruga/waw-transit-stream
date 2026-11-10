from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import override

import redis

from waw_transit.core import (
    ParameterlessReadRepository,
    ProviderParameterlessReadRepository,
    ProviderReadRepository,
    ReadRepository,
    VehicleSnapshot,
)
from waw_transit.database.redis.reader import run
from waw_transit.database.redis.session import RedisSession


def create_all_vehicles_reader() -> ParameterlessReadRepository[Sequence[VehicleSnapshot]]:
    return _AllVehiclesReader(RedisSession())


def create_line_vehicles_reader() -> ReadRepository[tuple[int, str], Sequence[VehicleSnapshot]]:
    return _LineVehiclesReader(RedisSession())


def create_vehicle_reader() -> ReadRepository[str, VehicleSnapshot | None]:
    return _VehicleReader(RedisSession())


class _AllVehiclesReader(
    ProviderParameterlessReadRepository[redis.Redis, Sequence[VehicleSnapshot]]
):

    def __init__(self, session: RedisSession) -> None:
        super().__init__(session)

    @override
    def load(self) -> Sequence[VehicleSnapshot]:
        hashes: tuple[_VehicleHash, ...] = run(
            self._provider,
            lambda client: tuple(
                _VehicleHash.from_redis(
                    _text(key).removeprefix("vehicle:"),
                    client.hgetall(key),
                )
                for key in client.scan_iter(match="vehicle:*")
            ),
            "Failed to load vehicles",
        )
        snapshots: Iterator[VehicleSnapshot | None] = (
            item.to_snapshot() for item in hashes
        )
        return tuple(snapshot for snapshot in snapshots if snapshot is not None)


class _LineVehiclesReader(
    ProviderReadRepository[redis.Redis, tuple[int, str], Sequence[VehicleSnapshot]]
):

    def __init__(self, session: RedisSession) -> None:
        super().__init__(session)

    @override
    def load(self, payload: tuple[int, str]) -> Sequence[VehicleSnapshot]:
        vehicle_type, line = payload
        hashes: tuple[_VehicleHash, ...] = run(
            self._provider,
            lambda client: tuple(
                _VehicleHash.from_redis(
                    member,
                    client.hgetall(f"vehicle:{_text(member)}"),
                )
                for member in client.smembers(f"line:{vehicle_type}:{line}")
            ),
            f"Failed to load line {vehicle_type}:{line}",
        )
        snapshots: Iterator[VehicleSnapshot | None] = (
            item.to_snapshot() for item in hashes
        )
        return tuple(snapshot for snapshot in snapshots if snapshot is not None)


class _VehicleReader(
    ProviderReadRepository[redis.Redis, str, VehicleSnapshot | None]
):

    def __init__(self, session: RedisSession) -> None:
        super().__init__(session)

    @override
    def load(self, payload: str) -> VehicleSnapshot | None:
        fields: Mapping[bytes | str, bytes | str] = run(
            self._provider,
            lambda client: client.hgetall(f"vehicle:{payload}"),
            f"Failed to load vehicle {payload}",
        )
        if not fields:
            return None
        return _VehicleHash.from_redis(payload, fields).to_snapshot()


@dataclass(frozen=True, slots=True)
class _VehicleHash:
    vehicle_id: str
    fields: Mapping[str, str]

    @classmethod
    def from_redis(
        cls,
        vehicle_id: bytes | str,
        fields: Mapping[bytes | str, bytes | str],
    ) -> _VehicleHash:
        return cls(
            vehicle_id=_text(vehicle_id),
            fields={_text(key): _text(value) for key, value in fields.items()},
        )

    def to_snapshot(self) -> VehicleSnapshot | None:
        try:
            vehicle_type, vehicle_number = self.vehicle_id.split(":", 1)
            return VehicleSnapshot(
                vehicle_type=int(vehicle_type),
                vehicle_number=vehicle_number,
                line=self.fields["line"],
                brigade=self.fields["brigade"],
                trip_id=self.fields["trip_id"],
                delay=float(self.fields["delay_sec"]),
                next_sequence=int(self.fields["next_stop_sequence"]),
                gtfs_version=int(self.fields["gtfs_version"]),
                timestamp=datetime.fromisoformat(self.fields["api_timestamp"]),
                lat=float(self.fields["lat"]),
                lon=float(self.fields["lon"]),
                match_status=self.fields["match_status"],
                next_stop=self.fields.get("next_stop") or None,
            )
        except (KeyError, TypeError, ValueError):
            return None


def _text(value: bytes | str) -> str:
    return value.decode() if isinstance(value, bytes) else value