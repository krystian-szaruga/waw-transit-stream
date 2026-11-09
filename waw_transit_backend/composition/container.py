from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from waw_transit.database.postgres.repository.stop_reader import (
    create_all_stops_reader,
    create_stop_reader,
)
from waw_transit.database.postgres.repository.trip_reader import create_lines_reader, create_trip_reader
from waw_transit.database.redis.departure_reader import create_stop_departures_reader
from waw_transit.database.redis.vehicle_reader import (
    create_all_vehicles_reader,
    create_line_vehicles_reader,
    create_vehicle_reader,
)
from waw_transit_backend.application.ports import Clock
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
        vehicle_service=VehicleService(
            create_all_vehicles_reader(),
            create_line_vehicles_reader(),
            create_vehicle_reader(),
            create_trip_reader(),
        ),
        stop_service=StopService(create_all_stops_reader(), create_stop_reader()),
        departure_service=DepartureService(
            create_stop_departures_reader(),
            create_stop_reader(),
            create_trip_reader(),
            _SystemClock(),
        ),
        line_service=LineService(create_lines_reader()),
        live_feed_service=None,
    )


class _SystemClock(Clock):

    def now(self) -> datetime:
        return datetime.now(ZoneInfo("Europe/Warsaw"))
