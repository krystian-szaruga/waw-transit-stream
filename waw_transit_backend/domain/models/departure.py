from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DepartureView:
    stop_id: str
    line: str
    direction: str
    vehicle_id: str
    scheduled: datetime
    predicted: datetime
    minutes: int
    delay_sec: float
