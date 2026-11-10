from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class StopInfo:
    stop_id: str
    name: str
    lat: float
    lon: float


@dataclass(frozen=True, slots=True)
class LineInfo:
    name: str
    vehicle_type: int


@dataclass(frozen=True, slots=True)
class TripStop:
    sequence: int
    name: str


@dataclass(frozen=True, slots=True)
class ScheduleQuery:
    stop_id: str
    service_dates: tuple[date, ...]


@dataclass(frozen=True, slots=True)
class ScheduledDeparture:
    stop_id: str
    trip_id: str
    line: str
    stop_sequence: int
    direction: str
    scheduled: datetime


@dataclass(frozen=True, slots=True)
class TripStopsQuery:
    trip_id: str
    service_date: date


@dataclass(frozen=True, slots=True)
class TripStopView:
    sequence: int
    name: str
    scheduled: datetime
