from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class VehicleResponse(BaseModel):
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


class StopResponse(BaseModel):
    id: str
    name: str
    lat: float
    lon: float


class LineResponse(BaseModel):
    name: str
    vehicle_type: int


class TripStopResponse(BaseModel):
    sequence: int
    name: str
    scheduled: datetime


class DepartureResponse(BaseModel):
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
