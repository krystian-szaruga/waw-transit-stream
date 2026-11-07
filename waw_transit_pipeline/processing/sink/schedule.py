from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import numpy as np

from waw_transit.core.models import StopDeparture
from waw_transit_pipeline.processing.model import Trip


@dataclass(frozen=True, slots=True)
class TripSchedule:
    _trip: Trip
    _tz: ZoneInfo
    _midnight: datetime = field(init=False, repr=False)

    def __post_init__(self) -> None:
        midnight = datetime.combine(self._trip.key.service_date, time.min, tzinfo=self._tz)
        object.__setattr__(self, "_midnight", midnight)

    def departures(self, delay: float, next_sequence: int) -> Iterator[StopDeparture]:
        for index in range(self._index(next_sequence), len(self._trip.seq)):
            scheduled = self._midnight + timedelta(seconds=float(self._trip.off[index]))
            predicted = scheduled + timedelta(seconds=delay)
            yield StopDeparture(
                stop_id=str(self._trip.stop_id[index]),
                stop_sequence=int(self._trip.seq[index]),
                scheduled=scheduled,
                predicted=predicted,
            )

    def _index(self, sequence: int) -> int:
        indices = np.flatnonzero(self._trip.seq == sequence)
        return int(indices[0]) if len(indices) else 0
