from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, override

import redis

from waw_transit.core import ProviderReadRepository, ReadRepository, StopDeparture
from waw_transit.database.redis.reader import run
from waw_transit.database.redis.session import RedisSession


def create_stop_departures_reader() -> ReadRepository[str, Sequence[StopDeparture]]:
    return _StopDeparturesReader(RedisSession())


class _StopDeparturesReader(
    ProviderReadRepository[redis.Redis, str, Sequence[StopDeparture]]
):

    def __init__(self, session: RedisSession) -> None:
        super().__init__(session)

    @override
    def load(self, payload: str) -> Sequence[StopDeparture]:
        entries: tuple[_DepartureEntry, ...] = run(
            self._provider,
            lambda client: tuple(
                entry
                for member, score in client.zrange(f"stop:{payload}", 0, -1, withscores=True)
                if (entry := _DepartureEntry.from_member(str(member), float(score))) is not None
            ),
            f"Failed to load departures for stop {payload}",
        )
        return tuple(
            StopDeparture(
                stop_id=payload,
                stop_sequence=entry.stop_sequence,
                scheduled=entry.scheduled,
                predicted=entry.predicted,
            )
            for entry in entries
        )

@dataclass(frozen=True, slots=True)
class _DepartureEntry:
    stop_sequence: int
    scheduled: datetime
    predicted: datetime

    @classmethod
    def from_member(cls, member: str, score: float) -> _DepartureEntry | None:
        try:
            data: dict[str, Any] = json.loads(member)
            return cls(
                stop_sequence=int(data["stop_sequence"]),
                scheduled=datetime.fromisoformat(data["scheduled"]),
                predicted=datetime.fromtimestamp(score, tz=timezone.utc),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None