from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd


@dataclass(frozen=True, slots=True)
class VehicleKey:
    vehicle_type: int
    vehicle_number: str


Anchor = tuple[float, float, datetime]


@dataclass(frozen=True, slots=True)
class MatchState:
    incumbent: str | None = None
    anchor: Anchor | None = None


@dataclass(frozen=True, slots=True)
class VehicleState:
    key: VehicleKey
    match: MatchState
    last_seen: datetime

    def record(self) -> dict:
        return {
            "incumbent": self.match.incumbent,
            "anchor": self.match.anchor,
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_record(cls, key: VehicleKey, record: dict) -> VehicleState:
        anchor = record["anchor"]
        parsed = None if anchor is None else (
            float(anchor[0]), float(anchor[1]), pd.Timestamp(anchor[2]).to_pydatetime()
        )
        return cls(
            key,
            MatchState(record["incumbent"], parsed),
            pd.Timestamp(record["last_seen"]).to_pydatetime(),
        )
