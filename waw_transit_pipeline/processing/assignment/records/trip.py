from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import NamedTuple

import numpy as np

from waw_transit_pipeline.processing.model import VehicleType


class TripKey(NamedTuple):
    service_date: date
    vehicle_type: VehicleType
    line: str
    brigade: str


@dataclass(frozen=True, slots=True)
class TripGeometry:
    a: np.ndarray
    d: np.ndarray
    len2: np.ndarray
    seg_len: np.ndarray
    seg_len_cum: np.ndarray
    seg_idx: np.ndarray
    seg_pos: np.ndarray
    first_xy: tuple[float, float]
    bbox: tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class Trip:
    key: TripKey
    trip_id: str
    route_id: str
    start: int
    end: int
    xy: np.ndarray
    off: np.ndarray
    stop_id: np.ndarray
    stop_name: np.ndarray
    seq: np.ndarray
    geom: TripGeometry
    off_delta: np.ndarray


@dataclass(frozen=True, slots=True)
class Match:
    trip: Trip
    dist_m: float
    delay_sec: float
    cost: float
    finished: bool = False
    seg: int = 0
    t: float = 0.0

    @property
    def waiting(self) -> bool:
        return self.seg == 0 and self.t < 0.05 and self.delay_sec < 0

    def as_row(self) -> tuple[str, float, float, float]:
        return self.trip.trip_id, self.dist_m, self.delay_sec, self.cost

    @staticmethod
    def no_match_row() -> tuple[None, None, None, None]:
        return None, None, None, None
