from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class DepartureView:
    stop_id: str
    line: str
    direction: str
    trip_id: str
    stop_sequence: int
    vehicle_next_sequence: int | None
    vehicle_id: str | None
    scheduled: datetime
    predicted: datetime | None
    scheduled_minutes: int
    minutes: int
    delay_sec: float | None
    live: bool


@dataclass(frozen=True, slots=True)
class ScheduledDeparture:
    stop_id: str
    trip_id: str
    line: str
    stop_sequence: int
    direction: str
    scheduled: datetime


@dataclass(frozen=True, slots=True)
class ScheduleQuery:
    stop_id: str
    service_dates: tuple[date, ...]
