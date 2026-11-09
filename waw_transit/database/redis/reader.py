from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import redis

from waw_transit.core import RepositoryError
from waw_transit.core.ports.repository.provider import Provider

Result = TypeVar("Result")


def run(
    provider: Provider[redis.Redis],
    operation: Callable[[redis.Redis], Result],
    message: str,
) -> Result:
    try:
        with provider.open() as client:
            return operation(client)
    except redis.RedisError as err:
        raise RepositoryError(f"{message}, reason: {err}") from err
