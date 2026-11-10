from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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
