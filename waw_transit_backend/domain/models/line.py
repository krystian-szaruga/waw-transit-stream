from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LineView:
    name: str
    vehicle_type: int
