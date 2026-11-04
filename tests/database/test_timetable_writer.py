from datetime import date

_COPY_COLUMNS = (
    "service_date, vehicle_type, line, brigade, route_id, trip_id, stop_id, stop_name, "
    "stop_sequence, stop_lat, stop_lon, scheduled_arrival_offset"
)


def _executed(cursor) -> list[str]:
    return [text for kind, text in cursor.events if kind == "execute"]


def test_when_copy_reports_rows_then_save_returns_that_count(make_writer, timetable_frame):
    writer, _ = make_writer(rowcount=3)

    assert writer.save(timetable_frame) == 3


def test_when_frame_spans_two_days_then_save_deletes_those_days_and_older(make_writer, timetable_frame):
    writer, cursor = make_writer()

    writer.save(timetable_frame)

    delete_sql = _executed(cursor)[0]
    assert "DELETE FROM public.static_timetable" in delete_sql
    assert "service_date = ANY(%s) OR service_date < %s" in delete_sql


def test_when_frame_has_repeated_days_then_delete_uses_unique_sorted_dates(make_writer, timetable_frame):
    writer, cursor = make_writer()

    writer.save(timetable_frame)

    _, params = cursor.executed[0]
    assert params == ([date(2026, 11, 4), date(2026, 11, 5)], date(2026, 11, 4))


def test_when_saving_then_copied_csv_has_no_header_and_iso_dates(make_writer, timetable_frame):
    writer, cursor = make_writer()

    writer.save(timetable_frame)

    lines = cursor.copies[0].strip().splitlines()
    assert len(lines) == 3
    assert not lines[0].startswith("service_date")
    assert [line.split(",")[0] for line in lines] == ["2026-11-05", "2026-11-04", "2026-11-04"]


def test_when_saving_then_copy_targets_the_table_with_frame_columns_in_order(make_writer, timetable_frame):
    writer, cursor = make_writer()

    writer.save(timetable_frame)

    copy_sql = next(text for kind, text in cursor.events if kind == "copy")
    assert copy_sql == (
        f"COPY public.static_timetable ({_COPY_COLUMNS}) FROM STDIN WITH (FORMAT csv)"
    )


def test_when_saving_then_primary_key_and_matching_index_are_recreated(make_writer, timetable_frame):
    writer, cursor = make_writer()

    writer.save(timetable_frame)

    statements = _executed(cursor)
    assert (
        "ALTER TABLE public.static_timetable ADD PRIMARY KEY "
        "(service_date, trip_id, stop_sequence)"
    ) in statements
    assert (
        "CREATE INDEX idx_timetable_matching ON public.static_timetable "
        "(service_date, vehicle_type, line, brigade)"
    ) in statements


def test_when_saving_then_indexes_are_dropped_before_copy_and_recreated_after(make_writer, timetable_frame):
    writer, cursor = make_writer()

    writer.save(timetable_frame)

    kinds = [kind for kind, _ in cursor.events]
    copy_at = kinds.index("copy")
    drop_index_at = next(i for i, (_, text) in enumerate(cursor.events) if text.startswith("DROP INDEX IF EXISTS"))
    drop_pk_at = next(i for i, (_, text) in enumerate(cursor.events) if "DROP CONSTRAINT IF EXISTS" in text)
    add_pk_at = next(i for i, (_, text) in enumerate(cursor.events) if "ADD PRIMARY KEY" in text)
    create_index_at = next(i for i, (_, text) in enumerate(cursor.events) if text.startswith("CREATE INDEX"))
    assert drop_index_at < copy_at
    assert drop_pk_at < copy_at
    assert add_pk_at > copy_at
    assert create_index_at > copy_at


def test_when_writer_targets_another_table_then_statements_use_custom_schema_and_table(make_writer, timetable_frame):
    writer, cursor = make_writer(schema="archive", table="static_timetable_2026")

    writer.save(timetable_frame)

    statements = [text for _, text in cursor.events]
    assert all("public." not in text for text in statements)
    assert all("archive." in text for text in statements)
    assert any("archive.static_timetable_2026" in text for text in statements)
    assert any("archive.idx_timetable_matching" in text for text in statements)
