from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from waw_transit_backend.adapters.outbound.postgres.scheduled_departures import (
    create_scheduled_departures_reader,
)
from waw_transit_backend.domain import ScheduleQuery

_TZ = ZoneInfo("Europe/Warsaw")


def test_when_reading_scheduled_departures_then_terminus_and_time_are_resolved(
    postgres: None,
) -> None:
    departures = create_scheduled_departures_reader().load(
        ScheduleQuery("1002", (date(2026, 11, 10),)),
    )

    departure = next(item for item in departures if item.trip_id == "t1")

    assert departure.line == "175"
    assert departure.stop_sequence == 2
    assert departure.direction == "Centrum"
    assert departure.scheduled == datetime(2026, 11, 10, 0, 2, tzinfo=_TZ)
