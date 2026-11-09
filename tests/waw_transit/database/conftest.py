from contextlib import contextmanager
from datetime import date

import pandas as pd
import psycopg2.extensions as ext
import pytest
from psycopg2 import sql

from waw_transit.core.ports.repository.provider import Provider
from waw_transit.database.postgres.cursor import create_provider
from waw_transit.database.postgres.repository import timetable_reader as reader_module
from waw_transit.database.postgres.repository import timetable_writer as writer_module


class _ReaderCursor:
    def __init__(self, csv: str, version_id: int = 7) -> None:
        self._csv = csv
        self._version_id = version_id
        self.copy_queries: list[str] = []
        self.executed: list[str] = []

    def execute(self, query, params=None) -> None:
        self.executed.append(query.as_string(self))

    def fetchone(self):
        return (self._version_id,)

    def copy_expert(self, query: str, file) -> None:
        self.copy_queries.append(query)
        file.write(self._csv)


class _WriterCursor:
    def __init__(self, rowcount: int = 0, rows: tuple = ()) -> None:
        self.rowcount = rowcount
        self.events: list[tuple[str, str]] = []
        self.executed: list[tuple[str, object]] = []
        self.copies: list[str] = []
        self._rows = list(rows)

    def execute(self, query, params=None) -> None:
        text = query.as_string(self)
        self.executed.append((text, params))
        self.events.append(("execute", text))

    def fetchone(self):
        return self._rows.pop(0)

    def copy_expert(self, query: str, file) -> None:
        self.events.append(("copy", query))
        self.copies.append(file.read())


class _FakeProvider(Provider):
    def __init__(self, cursor) -> None:
        self._cursor = cursor

    @contextmanager
    def open(self):
        yield self._cursor


@pytest.fixture(autouse=True)
def _quote_ident_without_connection(monkeypatch):
    monkeypatch.setattr(ext, "quote_ident", lambda name, context: name)
    monkeypatch.setattr(sql.Literal, "as_string", lambda self, context: f"'{self.wrapped}'")


@pytest.fixture
def make_reader(monkeypatch):
    def _make(csv: str, schema: str = "public", table: str = "static_timetable", version_id: int = 7):
        cursor = _ReaderCursor(csv, version_id)
        monkeypatch.setattr(reader_module, "create_provider", lambda: _FakeProvider(cursor))
        return reader_module.create_timetable_reader(schema, table), cursor

    return _make


@pytest.fixture
def make_writer(monkeypatch):
    def _make(
        rowcount: int = 0,
        rows: tuple = (),
        schema: str = "public",
        table: str = "static_timetable",
        versions_table: str = "gtfs_versions",
    ):
        cursor = _WriterCursor(rowcount, rows)
        monkeypatch.setattr(writer_module, "create_provider", lambda: _FakeProvider(cursor))
        return writer_module.create_timetable_writer(schema, table, versions_table), cursor

    return _make


@pytest.fixture
def timetable_csv() -> str:
    return (
        "service_date,vehicle_type,line,brigade,route_id,trip_id,stop_name,stop_id,"
        "stop_sequence,stop_lat,stop_lon,scheduled_arrival_offset\n"
        "2026-11-04,1,175,1,r1,t1,Plac Zawiszy,1001,1,52.2301,20.9901,0\n"
        "2026-11-04,1,175,1,r1,t1,Centrum,1002,2,52.2310,20.9910,120\n"
        "2026-11-05,2,9,3,r2,t2,Most Poniatowskiego,2001,1,52.2400,21.0300,60\n"
    )


@pytest.fixture
def timetable_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "service_date": [date(2026, 11, 5), date(2026, 11, 4), date(2026, 11, 4)],
            "vehicle_type": [2, 1, 1],
            "line": ["9", "175", "175"],
            "brigade": ["3", "1", "1"],
            "route_id": ["r2", "r1", "r1"],
            "trip_id": ["t2", "t1", "t1"],
            "stop_id": ["2001", "1001", "1002"],
            "stop_name": ["Most Poniatowskiego", "Plac Zawiszy", "Centrum"],
            "stop_sequence": [1, 1, 2],
            "stop_lat": [52.2400, 52.2301, 52.2310],
            "stop_lon": [21.0300, 20.9901, 20.9910],
            "scheduled_arrival_offset": [60, 0, 120],
        }
    )
