from __future__ import annotations

from collections.abc import Sequence

from waw_transit.core import ParameterlessReadRepository, ReadRepository, VehicleSnapshot
from waw_transit_backend.domain import NotFoundError, VehicleView


class VehicleService:

    def __init__(
        self,
        all_vehicles: ParameterlessReadRepository[Sequence[VehicleSnapshot]],
        line_vehicles: ReadRepository[tuple[int, str], Sequence[VehicleSnapshot]],
        vehicle_by_id: ReadRepository[str, VehicleSnapshot | None],
    ) -> None:
        self._all_vehicles = all_vehicles
        self._line_vehicles = line_vehicles
        self._vehicle_by_id = vehicle_by_id

    def all(self) -> Sequence[VehicleView]:
        return tuple(self._to_view(snapshot) for snapshot in self._all_vehicles.load())

    def by_line(self, vehicle_type: int, line: str) -> Sequence[VehicleView]:
        return tuple(
            self._to_view(snapshot)
            for snapshot in self._line_vehicles.load((vehicle_type, line))
        )

    def get(self, vehicle_id: str) -> VehicleView:
        snapshot: VehicleSnapshot | None = self._vehicle_by_id.load(vehicle_id)
        if snapshot is None:
            raise NotFoundError(f"Vehicle {vehicle_id} not found")
        return self._to_view(snapshot)

    def _to_view(self, snapshot: VehicleSnapshot) -> VehicleView:
        return VehicleView(
            id=snapshot.vehicle_id,
            type=snapshot.vehicle_type,
            number=snapshot.vehicle_number,
            line=snapshot.line,
            brigade=snapshot.brigade,
            trip_id=snapshot.trip_id,
            delay_sec=snapshot.delay,
            status=snapshot.match_status,
            next_stop=snapshot.next_stop,
            lat=snapshot.lat,
            lon=snapshot.lon,
        )
