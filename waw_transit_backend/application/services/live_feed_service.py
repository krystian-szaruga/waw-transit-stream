from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence

from waw_transit_backend.application.ports import LiveVehicleStream
from waw_transit_backend.application.services.departure_service import DepartureService
from waw_transit_backend.application.services.vehicle_service import VehicleService
from waw_transit_backend.domain import DepartureView, VehicleView


class LiveFeedService:
    _MIN_UPDATE_INTERVAL_SEC = 1.0

    def __init__(
        self,
        vehicles: VehicleService,
        departures: DepartureService,
        stream: LiveVehicleStream,
    ) -> None:
        self._vehicles = vehicles
        self._departures = departures
        self._stream = stream

    def snapshot(
        self,
        stop_id: str | None = None,
        line: str | None = None,
    ) -> list[VehicleView | DepartureView]:
        vehicles: list[VehicleView | DepartureView] = [
            vehicle
            for vehicle in self._vehicles.all()
            if line is None or vehicle.line == line
        ]
        if stop_id is None:
            return vehicles
        return vehicles + list(self._departures.for_stop(stop_id))

    async def updates(
        self,
        stop_id: str | None = None,
        line: str | None = None,
    ) -> AsyncIterator[list[VehicleView | DepartureView]]:
        loop = asyncio.get_running_loop()
        last = float("-inf")
        async for _ in self._stream.stream():
            now = loop.time()
            if now - last < self._MIN_UPDATE_INTERVAL_SEC:
                continue
            last = now
            yield await asyncio.to_thread(self.snapshot, stop_id, line)

    def departures_for(self, stop_id: str) -> Sequence[DepartureView]:
        return self._departures.for_stop(stop_id)
