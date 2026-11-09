from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from waw_transit_backend.adapters.inbound.http.schemas import DepartureResponse, VehicleResponse


class SubscribeMessage(BaseModel):
    type: Literal["subscribe"]
    line: str | None = None
    stop_id: str | None = None


class SnapshotMessage(BaseModel):
    type: Literal["snapshot"] = "snapshot"
    vehicles: list[VehicleResponse]
    departures: list[DepartureResponse]


class UpdateMessage(BaseModel):
    type: Literal["update"] = "update"
    vehicles: list[VehicleResponse]
    departures: list[DepartureResponse]
