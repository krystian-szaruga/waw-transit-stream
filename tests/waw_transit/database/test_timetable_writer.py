from waw_transit.core import Payload

_COPY_COLUMNS = (
    "gtfs_version, service_date, vehicle_type, line, brigade, route_id, trip_id, stop_id, "
    "stop_name, stop_sequence, stop_lat, stop_lon, scheduled_arrival_offset"
)
_SHA = "a" * 64


def _save(writer, frame) -> int:
    return writer.save(Payload(frame, _SHA))


def _executed(cursor) -> list[str]:
    return [text for kind, text in cursor.events if kind == "execute"]


def test_when_sha_is_new_then_save_returns_the_inserted_version(make_writer, timetable_frame):
    writer, _ = make_writer(rows=(None, (7,)))

    assert _save(writer, timetable_frame) == 7


def test_when_sha_is_known_then_save_returns_it_without_loading_anything(make_writer, timetable_frame):
    writer, cursor = make_writer(rows=((7,),))

    assert _save(writer, timetable_frame) == 7
    assert cursor.copies == []
    assert len(_executed(cursor)) == 1


def test_when_sha_is_new_then_the_version_row_is_inserted_with_that_sha(make_writer, timetable_frame):
    writer, cursor = make_writer(rows=(None, (7,)))

    _save(writer, timetable_frame)

    statement, params = cursor.executed[1]
    assert statement == (
        "INSERT INTO public.gtfs_versions (sha256) VALUES (%s) RETURNING version_id"
    )
    assert params == (_SHA,)


def test_when_saving_then_copied_csv_carries_the_version_and_iso_dates(make_writer, timetable_frame):
    writer, cursor = make_writer(rows=(None, (7,)))

    _save(writer, timetable_frame)

    lines = cursor.copies[0].strip().splitlines()
    assert len(lines) == 3
    assert not lines[0].startswith("gtfs_version")
    assert [line.split(",")[:2] for line in lines] == [
        ["7", "2026-11-05"],
        ["7", "2026-11-04"],
        ["7", "2026-11-04"],
    ]


def test_when_saving_then_copy_targets_the_table_with_the_version_column_first(make_writer, timetable_frame):
    writer, cursor = make_writer(rows=(None, (7,)))

    _save(writer, timetable_frame)

    copy_sql = next(text for kind, text in cursor.events if kind == "copy")
    assert copy_sql == (
        f"COPY public.static_timetable ({_COPY_COLUMNS}) FROM STDIN WITH (FORMAT csv)"
    )


def test_when_saving_then_the_previous_active_version_is_retired_before_the_new_one_activates(
    make_writer, timetable_frame
):
    writer, cursor = make_writer(rows=(None, (7,)))

    _save(writer, timetable_frame)

    statements = _executed(cursor)
    retire_at = next(
        i for i, text in enumerate(statements)
        if text == "UPDATE public.gtfs_versions SET status = 'retired' WHERE status = 'active'"
    )
    activate_at = next(
        i for i, text in enumerate(statements)
        if text == "UPDATE public.gtfs_versions SET status = 'active' WHERE version_id = %s"
    )
    assert retire_at < activate_at


def test_when_saving_then_rows_of_pruned_versions_are_deleted_before_the_versions(make_writer, timetable_frame):
    writer, cursor = make_writer(rows=(None, (7,)))

    _save(writer, timetable_frame)

    statements = _executed(cursor)
    rows_at = next(i for i, text in enumerate(statements)
                   if text.startswith("DELETE FROM public.static_timetable"))
    versions_at = next(i for i, text in enumerate(statements)
                       if text.startswith("DELETE FROM public.gtfs_versions"))
    assert rows_at < versions_at


def test_when_saving_then_active_and_three_newest_retired_versions_are_kept(make_writer, timetable_frame):
    writer, cursor = make_writer(rows=(None, (7,)))

    _save(writer, timetable_frame)

    prune = next(text for text in _executed(cursor)
                 if text.startswith("DELETE FROM public.gtfs_versions"))
    assert "status = 'active'" in prune
    assert "status = 'retired' ORDER BY loaded_at DESC LIMIT %s" in prune
    assert cursor.executed[-1][1] == (3,)


def test_when_writer_targets_another_schema_then_statements_use_it(make_writer, timetable_frame):
    writer, cursor = make_writer(rows=(None, (7,)), schema="archive", table="static_timetable_2026")

    _save(writer, timetable_frame)

    statements = [text for _, text in cursor.events]
    assert all("public." not in text for text in statements)
    assert any("archive.static_timetable_2026" in text for text in statements)
    assert any("archive.gtfs_versions" in text for text in statements)
