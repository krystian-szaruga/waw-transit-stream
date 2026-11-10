from dataclasses import replace
from datetime import date

import pytest

from waw_transit_pipeline.gtfs.loader.builder import ShapeBuilder, TimetableBuilder


def _shapes_for(gtfs_feed, service_date: date = date(2026, 11, 4)):
    timetable = TimetableBuilder(gtfs_feed, [service_date]).build()
    return ShapeBuilder(gtfs_feed).build(timetable["trip_id"])


def test_when_building_then_every_timetable_trip_gets_its_gtfs_shape(gtfs_feed):
    trips, _ = _shapes_for(gtfs_feed)
    by_trip = trips.set_index("trip_id")["shape_id"]

    assert by_trip.to_dict() == {"T-BUS-1": "SH-BUS-1", "T-TRAM-1": "SH-TRAM-1"}


def test_when_a_trip_is_outside_the_timetable_then_its_shape_is_not_stored(gtfs_feed):
    _, points = _shapes_for(gtfs_feed)

    assert set(points["shape_id"]) == {"SH-BUS-1", "SH-TRAM-1"}


def test_when_shape_points_are_unordered_then_they_come_back_sorted_by_sequence(gtfs_feed):
    _, points = _shapes_for(gtfs_feed)
    bus = points[points["shape_id"] == "SH-BUS-1"]

    assert bus["point_sequence"].tolist() == [0, 1, 2]
    assert bus["lat"].astype(float).tolist() == pytest.approx([52.23, 52.24, 52.25])


def test_when_two_trips_share_a_shape_then_its_points_are_stored_once(gtfs_feed):
    trips = gtfs_feed.trips.assign(
        shape_id=gtfs_feed.trips["shape_id"].replace({"SH-TRAM-1": "SH-BUS-1"})
    )
    feed = replace(gtfs_feed, trips=trips)
    timetable = TimetableBuilder(feed, [date(2026, 11, 4)]).build()

    trip_shapes, points = ShapeBuilder(feed).build(timetable["trip_id"])

    assert len(trip_shapes) == 2
    assert points["shape_id"].tolist() == ["SH-BUS-1", "SH-BUS-1", "SH-BUS-1"]


def test_when_building_then_columns_follow_the_shape_contract(gtfs_feed):
    trip_shapes, points = _shapes_for(gtfs_feed)

    assert list(trip_shapes.columns) == ["trip_id", "shape_id"]
    assert list(points.columns) == ["shape_id", "point_sequence", "lat", "lon"]


def test_when_building_then_coordinates_are_float32(gtfs_feed):
    _, points = _shapes_for(gtfs_feed)

    assert points["lat"].dtype == "float32"
    assert points["lon"].dtype == "float32"
