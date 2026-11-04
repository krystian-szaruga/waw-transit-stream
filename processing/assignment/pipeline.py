from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import pandas as pd
from pyspark import Broadcast
from pyspark.sql import DataFrame
from pyspark.sql.streaming.state import GroupState, GroupStateTimeout
import pyspark.sql.functions as F

from processing.model import Lookup, MatchStatus, TripMatchCol, WarsawLiveCol
from processing.assignment.ownership import TripOwnership
from processing.assignment.records import OwnershipRules, TripBounds, TripId
from processing.assignment.schema import Schema
from processing.assignment.state import BatchState
from processing.assignment.trip_matcher import TripMatcher
from processing.assignment.vehicle_matching import VehicleMatching


class AssignmentPipeline:
    _FRESH_WINDOW = "current_timestamp() - INTERVAL 3 MINUTES"

    def __init__(self, lookup_bc: Broadcast[Lookup]) -> None:
        self._lookup_bc = lookup_bc

    def build(self, live: DataFrame) -> DataFrame:
        line = F.trim(F.col(WarsawLiveCol.LINE))
        fresh = live.where(F.to_timestamp(F.col(WarsawLiveCol.TIME)) >= F.expr(self._FRESH_WINDOW))
        return (
            fresh.where(line.isNotNull() & (line != ""))
            .groupBy(WarsawLiveCol.VEHICLE_TYPE, WarsawLiveCol.LINE)
            .applyInPandasWithState(
                func=self._batch,
                outputStructType=Schema.output(),
                stateStructType=Schema.state(),
                outputMode="Append",
                timeoutConf=GroupStateTimeout.NoTimeout,
            )
        )

    def _batch(
            self,
            key: tuple[int, str],
            batches: Iterator[pd.DataFrame],
            state: GroupState,
    ) -> Iterator[pd.DataFrame]:
        return _Batch(self._lookup_bc, key, batches, state).run()


class _Batch:
    _RULES = OwnershipRules(switch_margin=300.0, ttl_sec=300.0, max_start_delay_sec=900)
    _LOOKUP_CACHE: dict[int, _LookupData] = {}

    def __init__(self, lookup_bc: Broadcast[Lookup], key: tuple[int, str], batches: Iterator[pd.DataFrame], state: GroupState) -> None:
        self._lookup_bc = lookup_bc
        self._key = key
        self._batches = batches
        self._state = state

    def run(self) -> Iterator[pd.DataFrame]:
        pings: pd.DataFrame | None = self._collect()
        if pings is None:
            self._state.remove()
            return iter(())
        now: pd.Timestamp = self._now(pings)
        batch_state = BatchState(self._state)
        batch_state.load()
        candidates: pd.DataFrame = self._match(pings, batch_state, now)
        wins: pd.DataFrame = self._own(candidates, batch_state, now)
        batch_state.save()
        return self._emit(wins, candidates)

    def _collect(self) -> pd.DataFrame | None:
        frames = [frame for frame in self._batches if not frame.empty]
        return pd.concat(frames, ignore_index=True) if frames else None

    @staticmethod
    def _now(pings: pd.DataFrame) -> pd.Timestamp:
        return pd.to_datetime(pings[WarsawLiveCol.TIME]).max()

    def _match(self, pings: pd.DataFrame, batch_state: BatchState, now: pd.Timestamp) -> pd.DataFrame:
        candidates, vehicles = VehicleMatching(self._lookup_data().matcher).match(pings, batch_state.vehicles, now)
        batch_state.set(vehicles, batch_state.owners)
        return candidates

    def _own(self, candidates: pd.DataFrame, held: BatchState, now: pd.Timestamp) -> pd.DataFrame:
        wins, owners = (
            TripOwnership(held.owners, self._lookup_data().bounds, self._RULES)
                        .resolve(candidates, now)
        )
        held.set(held.vehicles, owners)
        return wins

    @staticmethod
    def _emit(wins: pd.DataFrame, candidates: pd.DataFrame) -> Iterator[pd.DataFrame]:
        owned = wins[wins[TripMatchCol.MATCH_STATUS] != MatchStatus.LAYOVER]
        unmatched = candidates[candidates[TripMatchCol.TRIP_ID].isna()]
        frames = [frame for frame in (owned, unmatched) if not frame.empty]
        if not frames:
            return iter(())
        return iter([frames[0] if len(frames) == 1 else pd.concat(frames, ignore_index=True)])

    def _lookup_data(self) -> _LookupData:
        lookup = self._lookup_bc.value
        cached = self._LOOKUP_CACHE.get(id(lookup))
        if cached is None:
            cached = _LookupData(TripMatcher(lookup), self._trip_bounds(lookup))
            self._LOOKUP_CACHE.clear()
            self._LOOKUP_CACHE[id(lookup)] = cached
        return cached

    @staticmethod
    def _trip_bounds(lookup: Lookup) -> dict[TripId, TripBounds]:
        days: dict[object, pd.Timestamp] = {}
        bounds: dict[TripId, TripBounds] = {}
        for trip in lookup:
            midnight = days.get(trip.key.service_date)
            if midnight is None:
                midnight = pd.Timestamp(trip.key.service_date)
                days[trip.key.service_date] = midnight
                bounds[TripId(trip.trip_id)] = TripBounds(
                    midnight + pd.Timedelta(seconds=int(trip.start)),
                    midnight + pd.Timedelta(seconds=int(trip.end)),
                )
        return bounds


@dataclass(frozen=True, slots=True)
class _LookupData:
    matcher: TripMatcher
    bounds: dict[TripId, TripBounds]






