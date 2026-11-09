from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class TripStopView:
    sequence: int
    name: str
    scheduled: datetime


@dataclass(frozen=True, slots=True)
class TripStopsQuery:
    trip_id: str
    service_date: date
