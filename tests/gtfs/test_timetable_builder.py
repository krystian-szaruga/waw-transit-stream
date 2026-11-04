from datetime import date

import pandas as pd

from gtfs.loader.builder import TimetableBuilder

_EXPECTED_COLUMNS = [
    "service_date",
    "vehicle_type",
    "line",
    "brigade",
    "route_id",
    "trip_id",
    "stop_id",
    "stop_name",
    "stop_sequence",
    "stop_lat",
    "stop_lon",
    "scheduled_arrival_offset",
]


def test_when_only_one_day_is_requested_then_trips_from_other_days_are_skipped(gtfs_feed):
    timetable = TimetableBuilder(gtfs_feed, [date(2026, 11, 4)]).build()

    assert set(timetable["trip_id"]) == {"T-BUS-1", "T-TRAM-1"}


def test_when_calendar_marks_service_as_removed_then_its_trips_are_skipped(gtfs_feed):
    timetable = TimetableBuilder(gtfs_feed, [date(2026, 11, 4)]).build()

    assert "T-BUS-REMOVED" not in set(timetable["trip_id"])


def test_when_route_type_is_not_bus_or_tram_then_the_route_is_skipped(gtfs_feed):
    timetable = TimetableBuilder(gtfs_feed, [date(2026, 11, 4)]).build()

    assert "T-RAIL" not in set(timetable["trip_id"])


def test_when_building_then_gtfs_route_types_map_to_bus_and_tram(gtfs_feed):
    timetable = TimetableBuilder(gtfs_feed, [date(2026, 11, 4)]).build()
    by_trip = timetable.drop_duplicates("trip_id").set_index("trip_id")

    assert by_trip.loc["T-BUS-1", "vehicle_type"] == 1
    assert by_trip.loc["T-TRAM-1", "vehicle_type"] == 2


def test_when_building_then_line_and_brigade_come_from_route_and_block(gtfs_feed):
    timetable = TimetableBuilder(gtfs_feed, [date(2026, 11, 4)]).build()
    by_trip = timetable.drop_duplicates("trip_id").set_index("trip_id")

    assert by_trip.loc["T-BUS-1", "line"] == "175"
    assert by_trip.loc["T-BUS-1", "brigade"] == "B1"
    assert by_trip.loc["T-TRAM-1", "line"] == "9"
    assert by_trip.loc["T-TRAM-1", "brigade"] == "B2"


def test_when_building_then_stops_are_enriched_with_name_and_coordinates(gtfs_feed):
    timetable = TimetableBuilder(gtfs_feed, [date(2026, 11, 4)]).build()
    stop = timetable[
        (timetable["trip_id"] == "T-BUS-1") & (timetable["stop_sequence"] == 2)
    ].iloc[0]

    assert stop["stop_name"] == "Centrum"
    assert stop["stop_lat"] == 52.2310
    assert stop["stop_lon"] == 20.9910


def test_when_arrival_crosses_midnight_then_offset_continues_past_24h(gtfs_feed):
    timetable = TimetableBuilder(gtfs_feed, [date(2026, 11, 4)]).build()
    offsets = (
        timetable[timetable["trip_id"] == "T-BUS-1"]
        .sort_values("stop_sequence")["scheduled_arrival_offset"]
        .tolist()
    )

    assert offsets == [25200, 25800, 90300]


def test_when_building_then_columns_follow_the_timetable_contract(gtfs_feed):
    timetable = TimetableBuilder(gtfs_feed, [date(2026, 11, 4)]).build()

    assert list(timetable.columns) == _EXPECTED_COLUMNS


def test_when_building_for_today_and_tomorrow_then_both_days_are_included(gtfs_feed):
    timetable = TimetableBuilder.for_today_and_tomorrow(
        gtfs_feed, today=date(2026, 11, 4)
    ).build()

    assert set(timetable["service_date"]) == {date(2026, 11, 4), date(2026, 11, 5)}
    assert len(timetable) == 10


def test_when_service_starts_tomorrow_then_it_is_absent_from_today(gtfs_feed):
    timetable = TimetableBuilder.for_today_and_tomorrow(
        gtfs_feed, today=date(2026, 11, 4)
    ).build()

    assert set(timetable.loc[timetable["trip_id"] == "T-BUS-2", "service_date"]) == {
        date(2026, 11, 5)
    }


def test_when_a_time_crosses_midnight_then_offset_exceeds_one_day():
    offsets = TimetableBuilder.time_to_offset(pd.Series(["23:59:59", "25:30:00"]))

    assert offsets.tolist() == [86399, 91800]


def test_when_the_same_time_repeats_then_each_row_gets_the_same_offset():
    offsets = TimetableBuilder.time_to_offset(pd.Series(["07:05:00", "07:05:00"]))

    assert offsets.tolist() == [25500, 25500]


def test_when_time_has_leading_zeros_then_it_is_parsed_normally():
    offsets = TimetableBuilder.time_to_offset(pd.Series(["00:00:00", "07:05:09"]))

    assert offsets.tolist() == [0, 25509]
