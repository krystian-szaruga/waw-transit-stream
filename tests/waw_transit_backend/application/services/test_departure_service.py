from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from waw_transit.core import StopDepartureRecord, VehicleSnapshot
from waw_transit.core.models.static_state import StopInfo
from waw_transit_backend.application.services import DepartureService
from waw_transit_backend.domain import ScheduleQuery, ScheduledDeparture

_NOW = datetime(2026, 11, 9, 10, 0, tzinfo=ZoneInfo("Europe/Warsaw"))
_VEHICLE = VehicleSnapshot(
    vehicle_type=1,
    vehicle_number="2001",
    line="175",
    brigade="3",
    trip_id="live-trip",
    delay=120.0,
    next_sequence=2,
    gtfs_version=1,
    timestamp=_NOW,
    lat=52.23,
    lon=21.0,
    match_status="matched",
)


class _Clock:
    def now(self) -> datetime:
        return _NOW


class _Repository:
    def __init__(self, value) -> None:
        self._value = value

    def load(self, payload=None):
        return self._value


def _service(live: list[StopDepartureRecord], scheduled: list[ScheduledDeparture]) -> DepartureService:
    return DepartureService(
        _Repository(live),  # type: ignore[arg-type]
        _Repository(scheduled),  # type: ignore[arg-type]
        _Repository(StopInfo("1002", "Centrum", 52.23, 21.0)),  # type: ignore[arg-type]
        _Repository(()),  # type: ignore[arg-type]
        _Repository(_VEHICLE),  # type: ignore[arg-type]
        _Clock(),  # type: ignore[arg-type]
    )


def test_when_a_trip_is_live_then_prediction_wins_over_the_schedule() -> None:
    scheduled_moment = _NOW + timedelta(minutes=5)
    predicted = scheduled_moment + timedelta(minutes=2)
    live = StopDepartureRecord(
        stop_id="1002",
        vehicle_id="1:2001",
        vehicle_type=1,
        line="175",
        brigade="3",
        trip_id="live-trip",
        stop_sequence=2,
        scheduled=scheduled_moment,
        predicted=predicted,
    )
    scheduled = [
        ScheduledDeparture("1002", "live-trip", "175", 2, "Centrum", scheduled_moment),
        ScheduledDeparture("1002", "future-trip", "9", 1, "Gocław", _NOW + timedelta(minutes=12)),
    ]

    departures = _service([live], scheduled).for_stop("1002", 20)

    assert len(departures) == 2
    assert departures[0].trip_id == "live-trip"
    assert departures[0].stop_sequence == 2
    assert departures[0].vehicle_next_sequence == 2
    assert departures[0].live is True
    assert departures[0].predicted == predicted
    assert departures[0].scheduled_minutes == 5
    assert departures[0].delay_sec == 120.0
    assert departures[1].trip_id == "future-trip"
    assert departures[1].live is False
    assert departures[1].predicted is None
    assert departures[1].delay_sec is None


def test_when_only_the_schedule_has_a_trip_then_it_is_shown_without_prediction() -> None:
    scheduled = [
        ScheduledDeparture("1002", "future-trip", "9", 1, "Gocław", _NOW + timedelta(minutes=12)),
    ]

    departures = _service([], scheduled).for_stop("1002", 20)

    assert len(departures) == 1
    assert departures[0].vehicle_id is None
    assert departures[0].minutes == 12
