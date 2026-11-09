from __future__ import annotations

from dataclasses import dataclass


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
