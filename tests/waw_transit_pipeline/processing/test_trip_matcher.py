import pandas as pd
import pytest

from waw_transit_pipeline.processing.assignment.records import MatchState
from waw_transit_pipeline.processing.assignment.trip_matcher import TripMatcher
from waw_transit_pipeline.processing.model import MatchStatus

_TRIP_ID = 4
_DELAY_SEC = 6
_STATUS = 8
_VERSION = 10
_LON = 11
_LAT = 12
_NEXT_STOP = 13
_NEXT_STOP_NAME = 14


def _ping(timestamp: str, lon: float, lat: float = 52.25, line: str = "9") -> dict:
    return {
        "vehicle_type": 2,
        "VehicleNumber": "2001",
        "Brigade": "3",
        "Lines": line,
        "Lon": lon,
        "Lat": lat,
        "Time": pd.Timestamp(timestamp),
    }


def _match(lookup, *pings):
    frame = pd.DataFrame(list(pings))
    row, _, _ = TripMatcher(lookup, 7).match_rows(frame, MatchState())
    return row


def test_when_the_ping_is_inside_the_trip_then_the_trip_is_matched(load_lookup, timetable_frame):
    lookup = load_lookup(timetable_frame).lookup
    row = _match(lookup, _ping("2026-11-04 08:05:00", lon=21.025))
    from waw_transit_pipeline.processing.model import MatchStatus
    assert row[_STATUS] == MatchStatus.MATCHED
    assert row[_TRIP_ID] == "t2"
    assert row[_VERSION] == 7


def test_when_the_ping_is_on_schedule_then_the_delay_is_zero(load_lookup, timetable_frame):
    lookup = load_lookup(timetable_frame).lookup

    row = _match(lookup, _ping("2026-11-04 08:05:00", lon=21.025))

    assert row[_DELAY_SEC] == pytest.approx(0, abs=1e-6)


def test_when_the_ping_is_late_inside_the_tolerance_then_the_delay_is_positive(load_lookup, timetable_frame):
    lookup = load_lookup(timetable_frame).lookup

    row = _match(lookup, _ping("2026-11-04 08:10:00", lon=21.025))

    assert row[_STATUS] == MatchStatus.MATCHED
    assert row[_DELAY_SEC] == pytest.approx(300, abs=1e-3)


def test_when_the_ping_is_far_from_every_route_then_it_stays_unmatched(load_lookup, timetable_frame):
    lookup = load_lookup(timetable_frame).lookup

    row = _match(lookup, _ping("2026-11-04 08:05:00", lon=21.5))
    assert row[_STATUS] == MatchStatus.UNMATCHED
    assert row[_TRIP_ID] is None


def test_when_the_ping_arrives_after_the_trip_ended_then_it_stays_unmatched(load_lookup, timetable_frame):
    lookup = load_lookup(timetable_frame).lookup

    row = _match(lookup, _ping("2026-11-04 09:00:00", lon=21.025))

    assert row[_STATUS] == MatchStatus.UNMATCHED


def test_when_the_ping_arrives_before_the_trip_starts_then_it_stays_unmatched(load_lookup, timetable_frame):
    lookup = load_lookup(timetable_frame).lookup

    row = _match(lookup, _ping("2026-11-04 07:30:00", lon=21.02))

    assert row[_STATUS] == MatchStatus.UNMATCHED


def test_when_the_ping_is_matched_then_the_row_carries_its_position(load_lookup, timetable_frame):
    lookup = load_lookup(timetable_frame).lookup

    row = _match(lookup, _ping("2026-11-04 08:05:00", lon=21.025, lat=52.25))

    assert row[_LON] == pytest.approx(21.025)
    assert row[_LAT] == pytest.approx(52.25)


def test_when_the_ping_moves_along_the_trip_then_the_next_stop_is_the_segment_end(load_lookup, timetable_frame):
    lookup = load_lookup(timetable_frame).lookup

    row = _match(lookup, _ping("2026-11-04 08:05:00", lon=21.025))

    assert row[_NEXT_STOP] == 2
    assert row[_NEXT_STOP_NAME] == "Rondo"


def test_when_the_ping_is_unmatched_then_there_is_no_next_stop(load_lookup, timetable_frame):
    lookup = load_lookup(timetable_frame).lookup

    row = _match(lookup, _ping("2026-11-04 08:05:00", lon=21.5))

    assert row[_NEXT_STOP] is None
    assert row[_NEXT_STOP_NAME] is None
