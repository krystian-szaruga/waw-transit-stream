from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import NewType

import pandas as pd

OwnerKey = tuple[str, int, str]
TripId = NewType("TripId", str)


@dataclass(frozen=True, slots=True)
class TripOwner:
    trip_id: TripId
    vehicle_type: int
    vehicle_number: str
    cost: float
    last_seen: datetime

    def record(self) -> dict:
        return {
            "vehicle_type": self.vehicle_type,
            "vehicle_number": self.vehicle_number,
            "cost": self.cost,
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_record(cls, trip_id: TripId, record: dict) -> TripOwner:
        return cls(
            trip_id,
            int(record["vehicle_type"]),
            str(record["vehicle_number"]),
            float(record["cost"]),
            pd.Timestamp(record["last_seen"]).to_pydatetime(),
        )


@dataclass(frozen=True, slots=True)
class TripBounds:
    started_at: pd.Timestamp
    ended_at: pd.Timestamp


@dataclass(frozen=True, slots=True)
class OwnershipRules:
    switch_margin: float
    ttl_sec: float
    max_start_delay_sec: int
