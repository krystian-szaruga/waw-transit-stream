from __future__ import annotations

from collections.abc import Sequence

from waw_transit.core import ParameterlessReadRepository
from waw_transit.core.models.static_state import LineInfo
from waw_transit_backend.domain import LineView


class LineService:

    def __init__(self, lines: ParameterlessReadRepository[Sequence[LineInfo]]) -> None:
        self._lines = lines

    def all(self) -> Sequence[LineView]:
        return tuple(_to_view(line) for line in self._lines.load())


def _to_view(line: LineInfo) -> LineView:
    return LineView(name=line.name, vehicle_type=line.vehicle_type)
