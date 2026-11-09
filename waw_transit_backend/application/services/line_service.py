from __future__ import annotations

from collections.abc import Sequence

from waw_transit.core import ReadRepository
from waw_transit_backend.domain import LineView


class LineService:

    def __init__(self, live_state: ReadRepository, timetable: ReadRepository) -> None:
        pass

    def all(self) -> Sequence[LineView]:
        pass
