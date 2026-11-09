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


class DepartureResponse(BaseModel):
    stop_id: str
    line: str
    direction: str
    vehicle_id: str
    scheduled: datetime
    predicted: datetime
    minutes: int
    delay_sec: float
