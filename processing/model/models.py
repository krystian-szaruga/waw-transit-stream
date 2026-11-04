import bisect
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from enum import IntEnum, StrEnum
from functools import cached_property
from typing import NamedTuple, Iterator, Iterable, Mapping

import numpy as np

from processing.model.const import M_PER_DEG


class MatchStatus(StrEnum):
    MATCHED = "matched"
    LAYOVER = "layover"
    UNMATCHED = "unmatched"


class TripMatchCol(StrEnum):
    VEHICLE_TYPE = "vehicle_type"
    VEHICLE_NUMBER = "vehicle_number"
    BRIGADE = "brigade"
    LINE = "line"
    TRIP_ID = "trip_id"
    DIST_M = "dist_m"
    DELAY_SEC = "delay_sec"
    COST = "cost"
    MATCH_STATUS = "match_status"
    API_TS = "api_timestamp"


class WarsawLiveCol(StrEnum):
    """fields of the Warsaw API payload (values = JSON keys)"""
    LINE = "Lines"
    BRIGADE = "Brigade"
    VEHICLE_NUMBER = "VehicleNumber"
    LON = "Lon"
    LAT = "Lat"
    TIME = "Time"
    # derived from the Kafka topic, not part of the payload
    VEHICLE_TYPE = "vehicle_type"

class VehicleType(IntEnum):
    BUS = 1
    TRAM = 2


class TripKey(NamedTuple):
    """Identifies all trips of one brigade on one service day."""
    service_date: date
    vehicle_type: VehicleType
    line: str
    brigade: str


@dataclass(slots=True, frozen=True)
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


@dataclass(slots=True, frozen=True)
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


_LineKey = tuple[date, VehicleType, str]


class TripIndex:
    """Trips grouped by (service_date, vehicle_type, line); brigade is ignored."""

    def __init__(self, trips_by_key: Mapping[TripKey, list[Trip]]) -> None:
        self._idx = self._create_index(trips_by_key)
        self._starts = {
            key: np.fromiter((trip.start for trip in trips), dtype=np.int64, count=len(trips))
            for key, trips in self._idx.items()
        }
        self._max_duration = {
            key: max(trip.end - trip.start for trip in trips) for key, trips in self._idx.items()
        }

    @staticmethod
    def _create_index(trips_by_key: Mapping[TripKey, list[Trip]]) -> dict[_LineKey, list[Trip]]:
        grouped: defaultdict[_LineKey, list[Trip]] = defaultdict(list)
        for key, trips in trips_by_key.items():
            grouped[(key.service_date, key.vehicle_type, key.line)].extend(trips)
        return {k: sorted(v, key=lambda t: t.start) for k, v in grouped.items()}

    def get(self, service_date: date, vehicle_type: VehicleType, line: str) -> list[Trip]:
        return self._idx.get((service_date, vehicle_type, line), [])

    def active(
            self,
            service_date: date,
            vehicle_type: VehicleType,
            line: str,
            sec: float,
            layover_tol_sec: float,
            post_end_grace_sec: float,
    ) -> list[Trip]:
        key = (service_date, vehicle_type, line)
        trips = self._idx.get(key)
        if not trips:
            return []
        starts = self._starts[key]
        low = sec - post_end_grace_sec - self._max_duration[key]
        high = sec + layover_tol_sec
        left = bisect.bisect_left(starts, low)
        right = bisect.bisect_right(starts, high)
        return [
            trip for trip in trips[left:right]
            if trip.start - layover_tol_sec <= sec <= trip.end + post_end_grace_sec
        ]


class Lookup:
    """Trips grouped by TripKey, plus the projection factor used for stop coords."""

    def __init__(self, k: float) -> None:
        self._k = k
        self._trips: dict[TripKey, list[Trip]] = {}

    @property
    def k(self) -> float:
        return self._k

    def project(self, lon: float, lat: float) -> tuple[float, float]:
        """Project streaming lon/lat the same way stops were projected."""
        return lon * self._k * M_PER_DEG, lat * M_PER_DEG

    def extend(self, trips: Iterable[Trip]) -> None:
        for trip in trips:
            self._add(trip)

    def trips_for(self, service_date: date, vehicle_type: VehicleType, line: str) -> list[Trip]:
        return self._trip_index.get(service_date, vehicle_type, line)

    def active_trips(
            self,
            service_date: date,
            vehicle_type: VehicleType,
            line: str,
            sec: float,
            layover_tol_sec: float,
            post_end_grace_sec: float,
    ) -> list[Trip]:
        return self._trip_index.active(
            service_date, vehicle_type, line, sec, layover_tol_sec, post_end_grace_sec
        )

    def _add(self, trip: Trip) -> None:
        self._trips.setdefault(trip.key, []).append(trip)
        self.__dict__.pop("_trip_index", None)
    
    @cached_property
    def _trip_index(self) -> TripIndex:
        return TripIndex(self._trips)

    def __getstate__(self) -> dict:
        state = self.__dict__.copy()
        state.pop("_trip_index", None)
        return state

    def __contains__(self, key: TripKey) -> bool:
        return key in self._trips

    def __iter__(self) -> Iterator[Trip]:
        for trips in self._trips.values():
            yield from trips

    def __len__(self) -> int:
        return sum(len(t) for t in self._trips.values())


@dataclass(slots=True, frozen=True)
class Match:
    trip: Trip
    dist_m: float
    delay_sec: float        # positive = late, negative = early
    cost: float
    finished: bool = False
    seg: int = 0
    t: float = 0.0          # position on the segment, 0..1

    @property
    def waiting(self) -> bool:
        """Standing at the first stop, before the scheduled departure."""
        return self.seg == 0 and self.t < 0.05 and self.delay_sec < 0

    def as_row(self) -> tuple[str, float, float, float]:
        return self.trip.trip_id, self.dist_m, self.delay_sec, self.cost

    @staticmethod
    def no_match_row() -> tuple[None, None, None, None]:
        return None, None, None, None


Anchor = tuple[float, float, datetime]


@dataclass(frozen=True, slots=True)
class MatchState:
    """Per-vehicle state carried between batches."""
    incumbent: str | None = None
    anchor: Anchor | None = None