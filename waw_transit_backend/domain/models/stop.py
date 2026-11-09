from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StopView:
    id: str
    name: str
    lat: float
    lon: float
