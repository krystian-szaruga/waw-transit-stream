from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator
from typing import override

import psycopg2
from psycopg2.extensions import cursor

from core import ConfigLoader
from core import Provider


@dataclass(frozen=True)
class _PgParams:
    dsn: str
    user: str
    password: str
    db_host: str
    db_port: int
    db_name: str
    schema: str = "public"
    application_name: str = "transit"
    connect_timeout: int = 10


class _DatabaseConfigLoader(ConfigLoader):
    @override
    def  _read(self) -> _PgParams:
        host = self._env_reader.get("DB_HOST", "127.0.0.1")
        port = self._env_reader.get_int("DB_PORT", 5432)
        name = self._env_reader.get("DB_NAME", "warsaw_transit")
        return _PgParams(
            dsn=f"host={host} port={port} dbname={name}",
            user=self._env_reader.require("DB_USER"),
            password=self._env_reader.require("DB_PASSWORD"),
            db_host=self._env_reader.get("DB_HOST", "127.0.0.1"),
            db_port=self._env_reader.get_int("DB_PORT", 5432),
            db_name=self._env_reader.get("DB_NAME", "warsaw_transit"),
            schema=self._env_reader.get("DB_SCHEMA", "public"),
            application_name="waw-transit",
        )


class PgCursorProvider(Provider[cursor]):
    def __init__(self, pg: _PgParams, *, autocommit: bool = False) -> None:
        self._pg = pg
        self._autocommit = autocommit

    @contextmanager
    @override
    def open(self) -> Iterator[cursor]:
        conn = psycopg2.connect(
            self._pg.dsn, user=self._pg.user, password=self._pg.password,
            connect_timeout=self._pg.connect_timeout,
            application_name=self._pg.application_name,
        )
        try:
            conn.autocommit = self._autocommit
            with conn, conn.cursor() as cur:
                yield cur
        finally:
            conn.close()


def create_provider() -> PgCursorProvider:
    return PgCursorProvider(_DatabaseConfigLoader().load())