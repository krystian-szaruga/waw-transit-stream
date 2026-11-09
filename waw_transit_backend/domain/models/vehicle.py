from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VehicleView:
    id: str
    type: int
    number: str
    line: str
    brigade: str
    trip_id: str
    delay_sec: float
    status: str
    next_stop: str | None
    lat: float
    lon: float
