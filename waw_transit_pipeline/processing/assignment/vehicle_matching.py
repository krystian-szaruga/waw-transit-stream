from __future__ import annotations

from datetime import datetime

import pandas as pd

from waw_transit_pipeline.processing.model import TripMatchCol, WarsawLiveCol
from waw_transit_pipeline.processing.assignment.records import MatchState, VehicleKey, VehicleState
from waw_transit_pipeline.processing.assignment.trip_matcher import TripMatcher


class VehicleMatching:
    _STALE_SEC = 1800.0
    _COLUMNS = [column.value for column in TripMatchCol]
    _FLOAT = (TripMatchCol.DIST_M, TripMatchCol.DELAY_SEC, TripMatchCol.COST)

    def __init__(self, matcher: TripMatcher) -> None:
        self._matcher = matcher

    def match(
            self,
            pings: pd.DataFrame,
            vehicles: dict[VehicleKey, VehicleState],
            now: pd.Timestamp,
    ) -> tuple[pd.DataFrame, dict[VehicleKey, VehicleState]]:
        rows: list[tuple] = []
        updated: dict[VehicleKey, VehicleState] = {}
        for _, group in pings.groupby([WarsawLiveCol.VEHICLE_TYPE, WarsawLiveCol.VEHICLE_NUMBER], sort=False):
            key = self._key_of(group)
            held = vehicles.get(key, VehicleState(key, MatchState(), now.to_pydatetime()))
            row, last_ts, state = self._match_vehicle(group, held, now)
            seen = now if last_ts is None else last_ts
            updated[key] = VehicleState(key, state, pd.Timestamp(seen).to_pydatetime())
            if row is not None:
                rows.append(row)
        return self._frame(rows), updated

    def _match_vehicle(
            self,
            group: pd.DataFrame,
            state: VehicleState,
            now: pd.Timestamp,
    ) -> tuple[tuple | None, datetime | None, MatchState]:
        held = state.match if self._alive(state, now) else MatchState()
        return self._matcher.match_rows(group, held)

    def _alive(self, state: VehicleState, now: pd.Timestamp) -> bool:
        return (now - pd.Timestamp(state.last_seen)).total_seconds() <= self._STALE_SEC

    def _frame(self, rows: list[tuple]) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame(columns=self._COLUMNS)
        data = {
            column.value: [row[index] for row in rows]
            for index, column in enumerate(TripMatchCol)
        }
        data[TripMatchCol.API_TS.value] = pd.DatetimeIndex(data[TripMatchCol.API_TS.value]).tolist()
        frame = pd.DataFrame(data)
        frame[TripMatchCol.TRIP_ID.value] = frame[TripMatchCol.TRIP_ID.value].astype("string")
        frame[TripMatchCol.VEHICLE_TYPE.value] = frame[TripMatchCol.VEHICLE_TYPE.value].astype("int32")
        for column in self._FLOAT:
            frame[column.value] = frame[column.value].astype("float64")
        return frame[self._COLUMNS]

    @staticmethod
    def _key_of(group: pd.DataFrame) -> VehicleKey:
        vehicle_type = group[WarsawLiveCol.VEHICLE_TYPE].iloc[0]
        vehicle_number = group[WarsawLiveCol.VEHICLE_NUMBER].iloc[0]
        return VehicleKey(int(vehicle_type), str(vehicle_number))