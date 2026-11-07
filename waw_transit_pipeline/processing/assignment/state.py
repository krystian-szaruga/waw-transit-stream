from __future__ import annotations

import pickle

from pyspark.sql.streaming.state import GroupState

from waw_transit_pipeline.processing.assignment.records import TripId, TripOwner, VehicleKey, VehicleState


class BatchState:
    _VERSION = 1

    def __init__(self, state: GroupState) -> None:
        self._state = state
        self._vehicles: dict[VehicleKey, VehicleState] = {}
        self._owners: dict[TripId, TripOwner] = {}

    @property
    def vehicles(self) -> dict[VehicleKey, VehicleState]:
        return self._vehicles

    @property
    def owners(self) -> dict[TripId, TripOwner]:
        return self._owners

    def set(self, vehicles: dict[VehicleKey, VehicleState], owners: dict[TripId, TripOwner]) -> None:
        self._vehicles = vehicles
        self._owners = owners

    def load(self) -> None:
        if not self._state.exists:
            return
        vehicles, owners = self._state.get
        self._vehicles = self._load_vehicles(vehicles)
        self._owners = self._load_owners(owners)

    def save(self) -> None:
        self._state.update((
            pickle.dumps({
                "version": self._VERSION,
                "vehicles": {key: value.record() for key, value in self._vehicles.items()},
            }),
            pickle.dumps({
                "version": self._VERSION,
                "owners": {trip_id: owner.record() for trip_id, owner in self._owners.items()},
            }),
        ))

    def _load_vehicles(self, blob: bytes | None) -> dict[VehicleKey, VehicleState]:
        return {
            (_key := self._key(key)): VehicleState.from_record(_key, record)
            for key, record in self._records(blob, "vehicles").items()
        }

    def _load_owners(self, blob: bytes | None) -> dict[TripId, TripOwner]:
        return {
            (_trip_id := TripId(str(trip_id))): TripOwner.from_record(_trip_id, record)
            for trip_id, record in self._records(blob, "owners").items()
        }

    @staticmethod
    def _key(key: VehicleKey | tuple[int, str]) -> VehicleKey:
        if isinstance(key, VehicleKey):
            return key
        return VehicleKey(int(key[0]), str(key[1]))

    def _records(self, blob: bytes | None, key: str) -> dict:
        if blob is None:
            return {}
        data = pickle.loads(blob)
        if data.get("version") != self._VERSION:
            return {}
        return data.get(key, {})
