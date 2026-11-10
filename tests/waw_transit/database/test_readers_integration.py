from __future__ import annotations

from waw_transit.core import VehicleSnapshot
from waw_transit.core.models.static_state import LineInfo, ShapePoint, StopInfo, TripStop
from waw_transit.database.postgres.repository.trip_shape import create_trip_shape_reader
from waw_transit.database.postgres.repository.stop_reader import (
    create_all_stops_reader,
    create_stop_reader,
)
from waw_transit.database.postgres.repository.trip_reader import (
    create_lines_reader,
    create_trip_reader,
)
from waw_transit.database.redis.departure_reader import create_stop_departures_reader
from waw_transit.database.redis.vehicle_reader import (
    create_all_vehicles_reader,
    create_line_vehicles_reader,
    create_vehicle_reader,
)
from tests.infrastructure import API_TIMESTAMP, PREDICTED, SCHEDULED


def test_when_reading_all_stops_then_only_stops_of_the_active_version_are_returned(
    postgres: None,
) -> None:
    stops = create_all_stops_reader().load()

    assert [stop.name for stop in stops] == [
        "Centrum",
        "Plac Zawiszy",
        "Rondo Daszyńskiego",
        "Zajezdnia Wola",
    ]
    assert all(stop.stop_id != "9999" for stop in stops)


def test_when_reading_a_stop_then_the_active_version_is_used(postgres: None) -> None:
    reader = create_stop_reader()

    assert reader.load("1002") == StopInfo("1002", "Centrum", 52.2310, 20.9910)
    assert reader.load("9999") is None


def test_when_reading_a_trip_then_stops_come_in_sequence_order(postgres: None) -> None:
    trip = create_trip_reader().load("t1")

    assert trip == (TripStop(1, "Plac Zawiszy"), TripStop(2, "Centrum"))


def test_when_reading_lines_then_distinct_lines_of_the_active_version_are_returned(
    postgres: None,
) -> None:
    lines = create_lines_reader().load()

    assert lines == (LineInfo("175", 1), LineInfo("9", 2))


def test_when_reading_a_trip_shape_then_points_of_the_active_version_come_in_order(
    postgres: None,
) -> None:
    shape = create_trip_shape_reader().load("t1")

    assert shape == (
        ShapePoint(0, 52.2300, 20.9900),
        ShapePoint(1, 52.2310, 20.9910),
    )


def test_when_reading_a_shape_of_an_unknown_trip_then_it_is_empty(postgres: None) -> None:
    assert create_trip_shape_reader().load("unknown") == ()


def test_when_reading_all_vehicles_then_hashes_are_mapped_to_snapshots(
    redis_store: None,
) -> None:
    vehicles = create_all_vehicles_reader().load()

    assert {vehicle.vehicle_id for vehicle in vehicles} == {"1:2001", "2:3001"}


def test_when_reading_a_line_then_only_its_vehicles_are_returned(redis_store: None) -> None:
    vehicles = create_line_vehicles_reader().load((1, "175"))

    assert [vehicle.vehicle_id for vehicle in vehicles] == ["1:2001"]


def test_when_reading_a_vehicle_then_every_hash_field_is_mapped(redis_store: None) -> None:
    vehicle = create_vehicle_reader().load("1:2001")

    assert vehicle == VehicleSnapshot(
        vehicle_type=1,
        vehicle_number="2001",
        line="175",
        brigade="3",
        trip_id="t1",
        delay=45.5,
        next_sequence=2,
        gtfs_version=2,
        timestamp=API_TIMESTAMP,
        lat=52.23,
        lon=21.0,
        match_status="MATCHED",
        next_stop="Centrum",
    )


def test_when_reading_an_unknown_vehicle_then_none_is_returned(redis_store: None) -> None:
    assert create_vehicle_reader().load("9:9999") is None


def test_when_reading_departures_then_valid_entries_are_parsed_and_bad_ones_skipped(
    redis_store: None,
) -> None:
    departures = create_stop_departures_reader().load("1002")

    assert len(departures) == 1
    assert departures[0].stop_id == "1002"
    assert departures[0].stop_sequence == 2
    assert departures[0].scheduled == SCHEDULED
    assert departures[0].predicted == PREDICTED


def test_when_reading_an_unknown_stop_then_departures_are_empty(redis_store: None) -> None:
    assert create_stop_departures_reader().load("9999") == ()
