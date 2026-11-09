from __future__ import annotations

from collections.abc import Sequence

from waw_transit.core import ReadRepository
from waw_transit_backend.application.ports import Clock
from waw_transit_backend.domain import DepartureView


class DepartureService:

    def __init__(
        self,
        live_state: ReadRepository,
        timetable: ReadRepository,
        clock: Clock,
    ) -> None:
        pass

    def for_stop(self, stop_id: str, limit: int = 20) -> Sequence[DepartureView]:
        pass
