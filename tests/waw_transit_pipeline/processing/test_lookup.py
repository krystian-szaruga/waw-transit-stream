from datetime import date
from math import cos, radians

import pytest

from waw_transit_pipeline.processing.model import VehicleType, M_PER_DEG

_SERVICE_DATE = date(2026, 11, 4)


def test_when_frame_has_two_trips_then_lookup_holds_both_for_their_keys(load_lookup, timetable_frame):
    lookup = load_lookup(timetable_frame).lookup

    bus = lookup.trips_for(_SERVICE_DATE, VehicleType.BUS, "175")
    tram = lookup.trips_for(_SERVICE_DATE, VehicleType.TRAM, "9")

    assert [trip.trip_id for trip in bus] == ["t1"]
    assert [trip.trip_id for trip in tram] == ["t2"]
    assert len(lookup) == 2


def test_when_trip_is_built_then_offsets_come_from_the_stops(load_lookup, timetable_frame):
    lookup = load_lookup(timetable_frame).lookup

    trip = lookup.trips_for(_SERVICE_DATE, VehicleType.BUS, "175")[0]

    assert trip.off.tolist() == [86400, 88000]
    assert trip.start == 86400
    assert trip.end == 88000
    assert trip.off_delta.tolist() == [1600]


def test_when_trip_is_built_then_stop_identity_and_order_are_kept(load_lookup, timetable_frame):
    lookup = load_lookup(timetable_frame).lookup

    trip = lookup.trips_for(_SERVICE_DATE, VehicleType.TRAM, "9")[0]

    assert trip.stop_id.tolist() == ["2001", "2002"]
    assert trip.stop_name.tolist() == ["Most", "Rondo"]
    assert trip.seq.tolist() == [1, 2]
    assert trip.route_id == "r2"


def test_when_stops_are_projected_then_the_geometry_starts_at_the_first_stop(load_lookup, timetable_frame):
    lookup = load_lookup(timetable_frame).lookup

    trip = lookup.trips_for(_SERVICE_DATE, VehicleType.BUS, "175")[0]

    x, y = lookup.project(21.0, 52.23)
    assert trip.xy[0].tolist() == pytest.approx([x, y])
    assert trip.geom.first_xy == pytest.approx((x, y))
    assert trip.geom.seg_len.tolist() == pytest.approx([abs(x - lookup.project(21.006, 52.23)[0])])


def test_when_projecting_a_point_then_y_is_not_scaled_and_x_uses_the_latitude_factor(load_lookup, timetable_frame):
    lookup = load_lookup(timetable_frame).lookup

    x, y = lookup.project(21.0, 52.23)

    assert y == pytest.approx(52.23 * M_PER_DEG)
    assert x == pytest.approx(21.0 * cos(radians(52.23)) * M_PER_DEG)


def test_when_the_reader_reports_a_version_then_the_snapshot_carries_it(load_lookup, timetable_frame):
    snapshot = load_lookup(timetable_frame, version_id=11)

    assert snapshot.version_id == 11


def test_when_the_time_is_far_before_the_start_then_no_trip_is_active(load_lookup, timetable_frame):
    lookup = load_lookup(timetable_frame).lookup

    active = lookup.active_trips(_SERVICE_DATE, VehicleType.BUS, "175", 1000.0, 0.0, 600.0)

    assert active == []


def test_when_the_time_is_inside_the_trip_window_then_it_is_active(load_lookup, timetable_frame):
    lookup = load_lookup(timetable_frame).lookup

    active = lookup.active_trips(_SERVICE_DATE, VehicleType.BUS, "175", 87000.0, 0.0, 600.0)

    assert [trip.trip_id for trip in active] == ["t1"]
