from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from waw_transit.core import ParameterlessReadRepository
from waw_transit.database import (
    create_scheduled_departures_reader,
    create_trip_shape_reader,
    create_trip_stops_reader,
)
from waw_transit.database.postgres.repository.stop_reader import (
    create_all_stops_reader,
    create_stop_reader,
)
from waw_transit.database.postgres.repository.trip_reader import create_lines_reader, create_trip_reader
from waw_transit.database.redis import create_active_version_reader, create_live_vehicle_stream
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
    TripService,
    VehicleService,
)


@dataclass(frozen=True, slots=True)
class AppContainer:
    vehicle_service: VehicleService
    stop_service: StopService
    departure_service: DepartureService
    line_service: LineService
    trip_service: TripService
    live_feed_service: LiveFeedService
    active_version: ParameterlessReadRepository[int | None]


def create_container() -> AppContainer:
    vehicle_service = VehicleService(
        create_all_vehicles_reader(),
        create_line_vehicles_reader(),
        create_vehicle_reader(),
    )
    departure_service = DepartureService(
        create_stop_departures_reader(),
        create_scheduled_departures_reader(),
        create_stop_reader(),
        create_trip_reader(),
        create_vehicle_reader(),
        _SystemClock(),
    )
    return AppContainer(
        vehicle_service=vehicle_service,
        stop_service=StopService(create_all_stops_reader(), create_stop_reader()),
        departure_service=departure_service,
        line_service=LineService(create_lines_reader()),
        trip_service=TripService(create_trip_stops_reader(), create_trip_shape_reader()),
        live_feed_service=LiveFeedService(
            vehicle_service,
            departure_service,
            create_live_vehicle_stream(),
        ),
        active_version=create_active_version_reader(),
    )


class _SystemClock(Clock):

    def now(self) -> datetime:
        return datetime.now(ZoneInfo("Europe/Warsaw"))
