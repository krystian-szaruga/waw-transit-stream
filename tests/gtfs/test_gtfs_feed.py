import pandas as pd

from gtfs.loader.builder import GtfsFeed


def test_when_reading_zip_then_only_the_needed_columns_survive(gtfs_zip):
    feed = GtfsFeed.from_zip(gtfs_zip)

    assert list(feed.routes.columns) == ["route_id", "route_short_name", "route_type"]
    assert list(feed.trips.columns) == ["route_id", "service_id", "trip_id", "block_short_name"]
    assert list(feed.stop_times.columns) == ["trip_id", "stop_id", "stop_sequence", "arrival_time"]
    assert list(feed.stops.columns) == ["stop_id", "stop_name", "stop_lat", "stop_lon"]
    assert list(feed.calendar_dates.columns) == ["service_id", "date", "exception_type"]


def test_when_reading_zip_then_text_ids_stay_text_and_sequence_is_int(gtfs_zip):
    feed = GtfsFeed.from_zip(gtfs_zip)

    assert feed.stop_times["stop_sequence"].dtype == "int32"
    assert isinstance(feed.stops["stop_id"].iloc[0], str)
    assert isinstance(feed.stop_times["trip_id"].iloc[0], str)
    assert feed.calendar_dates["date"].iloc[0] == "20261104"


def test_when_reading_a_directory_then_it_yields_the_same_feed_as_the_zip(gtfs_directory, gtfs_zip):
    from_directory = GtfsFeed.from_directory(gtfs_directory)
    from_zip = GtfsFeed.from_zip(gtfs_zip)

    for name in ("routes", "trips", "stop_times", "stops", "calendar_dates"):
        pd.testing.assert_frame_equal(
            getattr(from_directory, name),
            getattr(from_zip, name),
        )
