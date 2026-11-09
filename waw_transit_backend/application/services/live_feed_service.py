from __future__ import annotations

from waw_transit_backend.application.ports import LiveVehicleStream
from waw_transit_backend.application.services.departure_service import DepartureService
from waw_transit_backend.application.services.vehicle_service import VehicleService
from waw_transit_backend.domain import DepartureView, VehicleView


class LiveFeedService:

    def __init__(
        self,
        vehicles: VehicleService,
        departures: DepartureService,
        stream: LiveVehicleStream,
    ) -> None:
        pass

    def snapshot(self, stop_id: str | None = None, line: str | None = None) -> list[VehicleView | DepartureView]:
        pass

    def updates(self):
        pass
