from __future__ import annotations

import numpy as np
import pandas as pd

from processing.model import TripMatchCol
from processing.assignment.records import OwnershipRules, TripBounds, TripId, TripOwner


class TripOwnership:
    def __init__(
            self,
            owners: dict[TripId, TripOwner],
            bounds: dict[TripId, TripBounds],
            rules: OwnershipRules,
    ) -> None:
        self._store = _OwnerStore(owners, bounds, rules.ttl_sec)
        self._bounds = bounds
        self._rules = rules

    def resolve(self, candidates: pd.DataFrame, now: pd.Timestamp) -> tuple[pd.DataFrame, dict[TripId, TripOwner]]:
        if candidates.empty:
            return candidates, self._store.owners

        clock = _ServiceClock(now)
        self._store.retain(clock)
        loop = _TripLoop(
            self._store,
            clock,
            self._bounds,
            self._rules.max_start_delay_sec,
            self._rules.switch_margin,
        )
        wins = loop.winners(candidates)
        return wins, self._store.owners


class _ServiceClock:
    def __init__(self, now: pd.Timestamp) -> None:
        self._now = pd.Timestamp(now)

    @property
    def now(self) -> pd.Timestamp:
        return self._now

    def seconds_since(self, timestamp: pd.Timestamp) -> float:
        return (self._now - timestamp).total_seconds()

    def stale(self, last_seen: pd.Timestamp, ttl_sec: float) -> bool:
        return self.seconds_since(pd.Timestamp(last_seen)) > ttl_sec


class _OwnerStore:
    def __init__(self, owners: dict[TripId, TripOwner], bounds: dict[TripId, TripBounds], ttl_sec: float) -> None:
        self._owners = dict(owners)
        self._bounds = bounds
        self._ttl_sec = ttl_sec

    @property
    def owners(self) -> dict[TripId, TripOwner]:
        return self._owners

    def get(self, trip_id: TripId) -> TripOwner | None:
        return self._owners.get(trip_id)

    def record(
            self,
            trip_id: TripId,
            vehicle_type: int,
            vehicle_number: str,
            cost: float,
            now: pd.Timestamp,
    ) -> None:
        self._owners[trip_id] = TripOwner(
            trip_id, vehicle_type, vehicle_number, cost, now.to_pydatetime()
        )

    def retain(self, clock: _ServiceClock) -> None:
        self._owners = {
            trip_id: owner for trip_id, owner in self._owners.items() if self._alive(clock, trip_id, owner)
        }

    def _alive(self, clock: _ServiceClock, trip_id: TripId, owner: TripOwner) -> bool:
        trip = self._bounds.get(trip_id)
        if trip is None:
            return not clock.stale(pd.Timestamp(owner.last_seen), self._ttl_sec)
        return clock.seconds_since(trip.ended_at) <= self._ttl_sec


class _TripLoop:
    def __init__(
            self,
            store: _OwnerStore,
            clock: _ServiceClock,
            bounds: dict[TripId, TripBounds],
            max_start_delay_sec: int,
            switch_margin: float,
    ) -> None:
        self._store = store
        self._clock = clock
        self._bounds = bounds
        self._max_delay = max_start_delay_sec
        self._margin = switch_margin

    def winners(self, candidates: pd.DataFrame) -> pd.DataFrame:
        trip_ids = candidates[TripMatchCol.TRIP_ID.value].to_numpy()
        costs = candidates[TripMatchCol.COST.value].to_numpy(dtype=float)
        vehicle_types = candidates[TripMatchCol.VEHICLE_TYPE.value].to_numpy()
        vehicle_numbers = candidates[TripMatchCol.VEHICLE_NUMBER.value].to_numpy()

        ranks: dict[TripId, int] = {}
        rank = np.empty(len(candidates), dtype=np.int64)
        for i, trip_id in enumerate(trip_ids):
            r = ranks.get(trip_id)
            if r is None:
                r = len(ranks)
                ranks[trip_id] = r
            rank[i] = r

        order = np.lexsort((costs, rank))
        count = len(ranks)
        best = np.full(count, -1, dtype=np.int64)
        holder = np.full(count, -1, dtype=np.int64)
        owners = [self._store.get(trip_id) for trip_id in ranks]

        for i in order:
            r = int(rank[i])
            if best[r] < 0:
                best[r] = i
            owner = owners[r]
            if owner is not None and int(vehicle_types[i]) == owner.vehicle_type:
                if str(vehicle_numbers[i]) == owner.vehicle_number:
                    holder[r] = i

        chosen: list[int] = []
        for r, trip_id in enumerate(ranks):
            owner = owners[r]
            pick = int(best[r])
            held = int(holder[r])
            if owner is not None and held >= 0 and not (costs[pick] < costs[held] - self._margin):
                pick = held
            if self._rejected(trip_id, owner, pick, vehicle_numbers):
                continue
            self._store.record(
                trip_id,
                int(vehicle_types[pick]),
                str(vehicle_numbers[pick]),
                float(costs[pick]),
                self._clock.now,
            )
            chosen.append(pick)

        return candidates.take(chosen).reset_index(drop=True)

    def _rejected(
            self,
            trip_id: TripId,
            owner: TripOwner | None,
            pick: int,
            vehicle_numbers: np.ndarray,
    ) -> bool:
        trip = self._bounds.get(trip_id)
        if trip is None or owner is None:
            return False
        if self._clock.seconds_since(trip.started_at) <= self._max_delay:
            return False
        return str(vehicle_numbers[pick]) != owner.vehicle_number
