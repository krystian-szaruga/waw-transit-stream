from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import cursor

from waw_transit.core import RepositoryError
from waw_transit.core.ports.repository.provider import Provider

Result = TypeVar("Result")


def run(
    provider: Provider[cursor],
    operation: Callable[[cursor], Result],
    message: str,
) -> Result:
    try:
        with provider.open() as cur:
            return operation(cur)
    except psycopg2.Error as err:
        raise RepositoryError(f"{message}, reason: {err}") from err


def fetch_all(
    cur: cursor,
    query: sql.Composable,
    params: tuple | None = None,
) -> list[tuple]:
    cur.execute(query, params)
    return cur.fetchall()


def fetch_one(
    cur: cursor,
    query: sql.Composable,
    params: tuple | None = None,
) -> tuple | None:
    cur.execute(query, params)
    return cur.fetchone()
