from __future__ import annotations

from dataclasses import dataclass

from waw_transit.database.postgres.repository.stop_reader import (
    create_all_stops_reader,
    create_stop_reader,
)
from waw_transit_backend.application.services import (
    DepartureService,
    LineService,
    LiveFeedService,
    StopService,
    VehicleService,
)


@dataclass(frozen=True, slots=True)
class AppContainer:
    vehicle_service: VehicleService
    stop_service: StopService
    departure_service: DepartureService
    line_service: LineService
    live_feed_service: LiveFeedService


def create_container() -> AppContainer:
    return AppContainer(
        vehicle_service=None,
        stop_service=StopService(create_all_stops_reader(), create_stop_reader()),
        departure_service=None,
        line_service=None,
        live_feed_service=None,
    )
