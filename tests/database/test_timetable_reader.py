from datetime import date

_COLUMNS = [
    "service_date",
    "vehicle_type",
    "line",
    "brigade",
    "route_id",
    "trip_id",
    "stop_name",
    "stop_id",
    "stop_sequence",
    "stop_lat",
    "stop_lon",
    "scheduled_arrival_offset",
]


def test_when_copy_returns_rows_then_load_returns_all_of_them(make_reader, timetable_csv):
    reader, _ = make_reader(timetable_csv)

    frame = reader.load([date(2026, 11, 4), date(2026, 11, 5)])

    assert frame["trip_id"].tolist() == ["t1", "t1", "t2"]
    assert frame["stop_sequence"].tolist() == [1, 2, 1]


def test_when_copy_returns_rows_then_service_date_is_a_real_date(make_reader, timetable_csv):
    reader, _ = make_reader(timetable_csv)

    frame = reader.load([date(2026, 11, 4)])

    assert frame["service_date"].tolist() == [date(2026, 11, 4), date(2026, 11, 4), date(2026, 11, 5)]


def test_when_copy_returns_rows_then_dtypes_follow_the_timetable_contract(make_reader, timetable_csv):
    reader, _ = make_reader(timetable_csv)

    frame = reader.load([date(2026, 11, 4)])

    assert frame["vehicle_type"].dtype == "int16"
    assert frame["line"].dtype == "string"
    assert frame["brigade"].dtype == "string"
    assert frame["stop_id"].dtype == "string"
    assert frame["stop_sequence"].dtype == "int32"
    assert frame["stop_lat"].dtype == "float64"
    assert frame["stop_lon"].dtype == "float64"
    assert frame["scheduled_arrival_offset"].dtype == "int32"


def test_when_loading_dates_then_copy_query_filters_exactly_those_days(make_reader, timetable_csv):
    reader, cursor = make_reader(timetable_csv)

    reader.load([date(2026, 11, 4), date(2026, 11, 5)])

    query = cursor.copy_queries[0]
    assert "service_date = ANY(ARRAY['2026-11-04', '2026-11-05']::date[])" in query
    assert "ORDER BY service_date, trip_id, stop_sequence" in query


def test_when_reader_targets_another_table_then_copy_query_uses_it(make_reader, timetable_csv):
    reader, cursor = make_reader(
        timetable_csv,
        schema="gtfs",
        table="static_timetable_archive",
    )

    reader.load([date(2026, 11, 4)])

    assert "FROM gtfs.static_timetable_archive" in cursor.copy_queries[0]


def test_when_copy_returns_only_a_header_then_load_returns_empty_frame(make_reader):
    header = ",".join(_COLUMNS) + "\n"
    reader, _ = make_reader(header)

    frame = reader.load([date(2026, 11, 4)])

    assert frame.empty
    assert list(frame.columns) == _COLUMNS
