from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, override

import redis

from waw_transit.core import ProviderReadRepository, ReadRepository, StopDepartureRecord
from waw_transit.database.redis.reader import run
from waw_transit.database.redis.session import RedisSession


def create_stop_departures_reader() -> ReadRepository[str, Sequence[StopDepartureRecord]]:
    return _StopDeparturesReader(RedisSession())


class _StopDeparturesReader(
    ProviderReadRepository[redis.Redis, str, Sequence[StopDepartureRecord]]
):

    def __init__(self, session: RedisSession) -> None:
        super().__init__(session)

    @override
    def load(self, payload: str) -> Sequence[StopDepartureRecord]:
        entries: tuple[_DepartureEntry, ...] = run(
            self._provider,
            lambda client: tuple(
                entry
                for member, score in client.zrange(f"stop:{payload}", 0, -1, withscores=True)
                if (entry := _DepartureEntry.from_member(str(member), float(score))) is not None
            ),
            f"Failed to load departures for stop {payload}",
        )
        return tuple(entry.to_record(payload) for entry in entries)


@dataclass(frozen=True, slots=True)
class _DepartureEntry:
    vehicle_id: str
    vehicle_type: int
    line: str
    brigade: str
    trip_id: str
    stop_sequence: int
    scheduled: datetime
    predicted: datetime

    @classmethod
    def from_member(cls, member: str, score: float) -> _DepartureEntry | None:
        try:
            data: dict[str, Any] = json.loads(member)
            return cls(
                vehicle_id=str(data["vehicle_id"]),
                vehicle_type=int(data["vehicle_type"]),
                line=str(data["line"]),
                brigade=str(data["brigade"]),
                trip_id=str(data["trip_id"]),
                stop_sequence=int(data["stop_sequence"]),
                scheduled=datetime.fromisoformat(data["scheduled"]),
                predicted=datetime.fromtimestamp(score, tz=timezone.utc),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None

    def to_record(self, stop_id: str) -> StopDepartureRecord:
        return StopDepartureRecord(
            stop_id=stop_id,
            vehicle_id=self.vehicle_id,
            vehicle_type=self.vehicle_type,
            line=self.line,
            brigade=self.brigade,
            trip_id=self.trip_id,
            stop_sequence=self.stop_sequence,
            scheduled=self.scheduled,
            predicted=self.predicted,
        )
