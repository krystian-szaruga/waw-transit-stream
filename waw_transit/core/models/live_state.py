from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class LiveStateBatch:
    vehicles: tuple[VehicleSnapshot, ...]
    departures: Mapping[str, Sequence[StopDeparture]]


@dataclass(frozen=True, slots=True)
class VehicleSnapshot:
    vehicle_type: int
    vehicle_number: str
    line: str
    brigade: str
    trip_id: str
    delay: float
    next_sequence: int
    gtfs_version: int
    timestamp: datetime
    lat: float
    lon: float
    match_status: str

    @property
    def vehicle_id(self) -> str:
        return f"{self.vehicle_type}:{self.vehicle_number}"


@dataclass(frozen=True, slots=True)
class StopDeparture:
    stop_id: str
    stop_sequence: int
    scheduled: datetime
    predicted: datetime

    @property
    def score(self) -> float:
        return self.predicted.timestamp()


@dataclass(frozen=True, slots=True)
class StopDepartureRecord:
    stop_id: str
    vehicle_id: str
    vehicle_type: int
    line: str
    brigade: str
    trip_id: str
    stop_sequence: int
    scheduled: datetime
    predicted: datetime
