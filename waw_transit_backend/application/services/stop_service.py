from __future__ import annotations

from collections.abc import Sequence

from waw_transit.core import ParameterlessReadRepository, ReadRepository
from waw_transit.core.models.static_state import StopInfo
from waw_transit_backend.domain import NotFoundError, StopView


class StopService:

    def __init__(
        self,
        all_stops: ParameterlessReadRepository[Sequence[StopInfo]],
        stop_by_id: ReadRepository[str, StopInfo | None],
    ) -> None:
        self._all_stops = all_stops
        self._stop_by_id = stop_by_id

    def search(self, query: str | None = None) -> Sequence[StopView]:
        stops: Sequence[StopInfo] = self._all_stops.load()
        if query is None:
            return tuple(_to_view(stop) for stop in stops)
        needle = query.casefold()
        return tuple(
            _to_view(stop) for stop in stops if needle in stop.name.casefold()
        )

    def get(self, stop_id: str) -> StopView:
        stop: StopInfo | None = self._stop_by_id.load(stop_id)
        if stop is None:
            raise NotFoundError(f"Stop {stop_id} not found")
        return _to_view(stop)


def _to_view(stop: StopInfo) -> StopView:
    return StopView(
        id=stop.stop_id,
        name=stop.name,
        lat=stop.lat,
        lon=stop.lon,
    )
