from __future__ import annotations

from collections.abc import Sequence

from waw_transit.core import ReadRepository
from waw_transit_backend.domain import StopView


class StopService:

    def __init__(self, stops: ReadRepository) -> None:
        pass

    def search(self, query: str | None = None) -> Sequence[StopView]:
        pass

    def get(self, stop_id: str) -> StopView:
        pass
