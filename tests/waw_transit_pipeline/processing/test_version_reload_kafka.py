from __future__ import annotations

import io
import os
import zipfile
from datetime import date
from types import SimpleNamespace

import psycopg2
from confluent_kafka import Producer

from waw_transit.database import create_timetable_reader, create_timetable_writer, create_version_reader
from waw_transit_pipeline.adapters.kafka import open_version_watcher
from waw_transit_pipeline.adapters.kafka.publisher import _KafkaPublisher
from waw_transit_pipeline.gtfs.loader import TimetableLoader
from waw_transit_pipeline.gtfs.sync import TimetableSync
from waw_transit_pipeline.processing import ProcessingService
from waw_transit_pipeline.processing.config import ProcessingConfig


def test_when_gtfs_loads_a_new_version_then_processing_reloads_the_lookup(
    redpanda, postgres
) -> None:
    version_reader = create_version_reader()
    _advance_sequence()
    loaded_version = version_reader.load()
    created_version = loaded_version
    publisher = _KafkaPublisher(
        Producer({"bootstrap.servers": redpanda.bootstrap_servers}),
        redpanda.version_topic,
    )
    sync = TimetableSync(
        TimetableLoader(create_timetable_writer()),
        _State(),
        _Downloader(_gtfs_zip(date.today())),
        publisher,
    )

    try:
        sync.run()
        created_version = version_reader.load()

        with open_version_watcher(redpanda) as watcher:
            service = _service(watcher)

            noticed = service._await(_Console(), loaded_version)
            reloaded = service._reload(SimpleNamespace(version_id=loaded_version))
    finally:
        _restore(loaded_version, created_version)

    assert noticed is True
    assert reloaded.version_id == created_version
    assert {trip.trip_id for trip in reloaded.lookup} == {"t2"}


class _Downloader:
    def __init__(self, content: bytes) -> None:
        self._content = content

    def download(self, etag, last_modified):
        return SimpleNamespace(
            content=self._content,
            sha256="c" * 64,
            etag="etag",
            last_modified="last-modified",
        )


class _State:
    def get(self):
        return SimpleNamespace(etag=None, last_modified=None)

    def put(self, state) -> None:
        pass


class _Console:
    def __init__(self, active: bool = True) -> None:
        self.isActive = active


class _Sink:
    def save(self, frame) -> None:
        pass


class _StreamReader:
    def read(self, session):
        return None


class _VersionStore:
    def save(self, version_id: int) -> None:
        pass


def _service(watcher) -> ProcessingService:
    config = ProcessingConfig(checkpoint_location="/tmp/checkpoints")
    return ProcessingService(
        config,
        _Sink(),
        create_timetable_reader(),
        create_version_reader(),
        watcher,
        _VersionStore(),
        _StreamReader(),
    )


def _gtfs_zip(service_date: date) -> bytes:
    files = {
        "routes.txt": "route_id,route_short_name,route_type\nr9,9,0\n",
        "trips.txt": "route_id,service_id,trip_id,block_short_name\nr9,wk,t2,3\n",
        "stop_times.txt": (
            "trip_id,stop_id,stop_sequence,arrival_time\n"
            "t2,2001,1,08:00:00\n"
            "t2,2002,2,08:05:00\n"
        ),
        "stops.txt": (
            "stop_id,stop_name,stop_lat,stop_lon\n"
            "2001,Rondo Daszyńskiego,52.24,21.03\n"
            "2002,Zajezdnia Wola,52.25,21.04\n"
        ),
        "calendar_dates.txt": (
            "service_id,date,exception_type\n"
            f"wk,{service_date.strftime('%Y%m%d')},1\n"
        ),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def _restore(previous_version: int, created_version: int) -> None:
    with _connection() as connection:
        connection.autocommit = True
        with connection.cursor() as cur:
            cur.execute("DELETE FROM static_timetable WHERE gtfs_version = %s", (created_version,))
            cur.execute("DELETE FROM gtfs_versions WHERE version_id = %s", (created_version,))
            cur.execute(
                "UPDATE gtfs_versions SET status = 'active' WHERE version_id = %s",
                (previous_version,),
            )


def _advance_sequence() -> None:
    with _connection() as connection:
        connection.autocommit = True
        with connection.cursor() as cur:
            cur.execute(
                "SELECT setval("
                "pg_get_serial_sequence('gtfs_versions', 'version_id'), "
                "(SELECT max(version_id) FROM gtfs_versions))"
            )


def _connection():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
