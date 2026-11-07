import pandas as pd

from waw_transit_pipeline.processing.assignment.ownership import TripOwnership
from waw_transit_pipeline.processing.assignment.records import OwnershipRules, TripBounds, TripId, TripOwner

_NOW = pd.Timestamp("2026-11-04 09:00:00")
_RULES = OwnershipRules(switch_margin=300.0, ttl_sec=300.0, max_start_delay_sec=900)
_COLUMNS = ["vehicle_type", "vehicle_number", "trip_id", "cost"]


def _candidates(*rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=_COLUMNS)


def _bounds(trip_id: str, started: str, ended: str) -> dict[TripId, TripBounds]:
    return {TripId(trip_id): TripBounds(pd.Timestamp(started), pd.Timestamp(ended))}


def _owner(trip_id: str, number: str, cost: float) -> TripOwner:
    return TripOwner(TripId(trip_id), 1, number, cost, pd.Timestamp("2026-11-04 08:59:50").to_pydatetime())


def test_when_two_vehicles_claim_one_trip_then_the_cheaper_one_wins():
    ownership = TripOwnership({}, {}, _RULES)

    wins, owners = ownership.resolve(
        _candidates((1, "A", "t1", 50.0), (1, "B", "t1", 10.0)), _NOW
    )

    assert wins["vehicle_number"].tolist() == ["B"]
    assert owners[TripId("t1")].vehicle_number == "B"


def test_when_the_owner_is_slightly_worse_then_it_keeps_the_trip():
    ownership = TripOwnership({TripId("t1"): _owner("t1", "A", 100.0)}, {}, _RULES)

    wins, _ = ownership.resolve(
        _candidates((1, "A", "t1", 100.0), (1, "B", "t1", 60.0)), _NOW
    )

    assert wins["vehicle_number"].tolist() == ["A"]


def test_when_a_challenger_is_cheaper_by_more_than_the_margin_then_it_takes_over():
    ownership = TripOwnership({TripId("t1"): _owner("t1", "A", 500.0)}, {}, _RULES)

    wins, _ = ownership.resolve(
        _candidates((1, "A", "t1", 500.0), (1, "B", "t1", 100.0)), _NOW
    )

    assert wins["vehicle_number"].tolist() == ["B"]


def test_when_the_owner_is_stale_then_a_new_vehicle_becomes_the_owner():
    ownership = TripOwnership({TripId("t1"): _owner("t1", "A", 10.0)}, {}, _RULES)

    _, owners = ownership.resolve(_candidates((1, "B", "t1", 10.0)), _NOW)

    assert owners[TripId("t1")].vehicle_number == "B"


def test_when_the_trip_already_started_and_the_owner_is_another_vehicle_then_the_claim_is_rejected():
    bounds = _bounds("t1", "2026-11-04 08:40:00", "2026-11-04 09:10:00")
    ownership = TripOwnership({TripId("t1"): _owner("t1", "A", 5.0)}, bounds, _RULES)

    wins, _ = ownership.resolve(_candidates((1, "B", "t1", 10.0)), _NOW)

    assert wins.empty


def test_when_the_trip_has_not_started_yet_then_a_new_vehicle_may_claim_it():
    bounds = _bounds("t1", "2026-11-04 08:58:00", "2026-11-04 09:30:00")
    ownership = TripOwnership({TripId("t1"): _owner("t1", "A", 5.0)}, bounds, _RULES)

    wins, owners = ownership.resolve(_candidates((1, "B", "t1", 10.0)), _NOW)

    assert wins["vehicle_number"].tolist() == ["B"]
    assert owners[TripId("t1")].vehicle_number == "B"
