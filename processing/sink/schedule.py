from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

import numpy as np

from processing.model import Trip


@dataclass(frozen=True, slots=True)
class TripSchedule:
    _trip: Trip
    _tz: ZoneInfo
    _midnight: datetime = field(init=False, repr=False)

    def __post_init__(self) -> None:
        midnight = datetime.combine(self._trip.key.service_date, time.min, tzinfo=self._tz)
        object.__setattr__(self, "_midnight", midnight)

    def departures(self, delay: float, next_sequence: int) -> Iterator[_Departure]:
        for index in range(self._index(next_sequence), len(self._trip.seq)):
            scheduled = self._midnight + timedelta(seconds=float(self._trip.off[index]))
            predicted = scheduled + timedelta(seconds=delay)
            yield _Departure(
                stop_id=str(self._trip.stop_id[index]),
                score=predicted.timestamp(),
                stop_sequence=int(self._trip.seq[index]),
                scheduled=scheduled,
                predicted=predicted,
            )

    def _index(self, sequence: int) -> int:
        indices = np.flatnonzero(self._trip.seq == sequence)
        return int(indices[0]) if len(indices) else 0



class _Departure(NamedTuple):
    stop_id: str
    score: float  # predicted departure as a unix timestamp
    stop_sequence: int
    scheduled: datetime
    predicted: datetime