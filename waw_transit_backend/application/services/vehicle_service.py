from __future__ import annotations

from collections.abc import Sequence

from waw_transit.core import ReadRepository
from waw_transit_backend.domain import VehicleView


class VehicleService:

    def __init__(self, live_state: ReadRepository, timetable: ReadRepository) -> None:
        pass

    def all(self) -> Sequence[VehicleView]:
        pass

    def by_line(self, vehicle_type: int, line: str) -> Sequence[VehicleView]:
        pass

    def get(self, vehicle_id: str) -> VehicleView:
        pass
