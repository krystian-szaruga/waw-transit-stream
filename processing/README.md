# Processing: trip matching and ownership

## Goal

Move trip ownership from the driver-side `TripOwnershipArbiter` into a single
Spark stateful operator, so ownership state survives query restarts and scales
with the cluster.

## Current state

- `TripMatchStage` matches trips per vehicle with `applyInPandasWithState`
  grouped by `(vehicle_type, vehicle_number)`.
- `TripOwnershipArbiter` resolves duplicate `trip_id` assignments in
  `foreachBatch` on the driver.
- The driver-side arbiter was a deliberate temporary solution: Spark rejects
  two chained `applyInPandasWithState` operators with
  `Multiple applyInPandasWithStates are not supported on a streaming DataFrames/Datasets`.

Current results after the matching rules and the temporary arbiter:

- 99.9% of vehicles within `-5..+10 min`,
- `late > 10 min`: 0.1%,
- `early > 5 min`: 0%.

## Target design

Replace `TripMatchStage` + `TripOwnershipArbiter` with one stateful operator:

- name: `LineMatchStage`,
- key: `(vehicle_type, line)`,
- state: matching state per vehicle plus ownership state per trip,
- output: only the winning vehicle for each trip.

Grouping by line is required because trip ownership needs visibility of all
vehicles that can claim the same trip.

## State

Use one `BinaryType` state value containing a pickled, versioned dictionary:

```python
{
    "version": 1,
    "vehicles": {
        (vehicle_type, vehicle_number): {
            "incumbent": trip_id | None,
            "anchor": (x, y, timestamp) | None,
        }
    },
    "owners": {
        trip_id: {
            "vehicle_type": int,
            "vehicle_number": str,
            "cost": float,
            "last_seen": timestamp,
        }
    },
}
```

The state must be pruned:

- vehicles not seen for a configurable timeout,
- owners after `trip.end + post_end_grace_sec`.

## Algorithm per micro-batch

1. Concatenate all incoming pings for the line.
2. Group by vehicle.
3. For each vehicle, call the existing `TripMatcher.match_batch` logic with
   that vehicle's saved `incumbent` and `anchor`.
4. Keep the latest match per vehicle.
5. Resolve trip ownership across all vehicles in the batch.
6. Emit only the winning row for each `trip_id`.
7. Persist updated vehicle and ownership state.

## Matching and ownership rules to preserve

- `late_tol_sec = 3600`,
- `post_end_grace_sec = 600`,
- `early_tol_sec = 900`,
- `layover_tol_sec = 2400` only at the first stop,
- `waiting_tol_sec = 1200`,
- `max_dist_m = 200`,
- a future trip may match only the first segment when `sec < trip.start`,
- a trip is rejected when the vehicle is near its first stop and
  `sec - trip.start > max_start_delay_sec`,
- ownership switch margin: 300 cost units,
- an owner is kept until `trip.end + post_end_grace_sec`,
- a new owner cannot claim a trip after `trip.start + max_start_delay_sec`.

## Migration plan

1. Add `streaming` with `LineMatchStage`.
2. Reuse `TripMatcher` for per-vehicle matching instead of duplicating `_fit`.
3. Wire `LineMatchStage` in `processing/main.py`.
4. Use a new `checkpointLocation`; the old state schema is incompatible.
5. Run in shadow mode: log both `TripMatchStage` + arbiter and `LineMatchStage`
   results and compare ownership decisions.
6. Switch the console query and any writers to `LineMatchStage`.
7. Remove `TripOwnershipArbiter` and the old `TripMatchStage` if no longer used.
8. Update `debug_dump.py` so dumps reflect the final ownership decisions.

## Acceptance criteria

- No duplicate `trip_id -> vehicle_number` assignments in any batch.
- Restarting the query preserves ownership for trips still in progress.
- `late > 10 min` stays below 1%.
- `early > 5 min` stays at 0% in normal operation.
- Batch processing time stays below the 15 s trigger.
- The L53 `673:1004` case is rejected for the waiting vehicle.
- The L25 `02:0805` case no longer produces a 55-minute delay.

## Risks

- State size for busy lines.
- Checkpoint incompatibility requires a clean start.
- After-midnight trips need correct service-date handling in ownership timeouts.
- The driver-side arbiter is easier to debug; the Spark-native version needs
  equivalent diagnostics.
- Brigade data remains unreliable and must not be used as a hard filter.

## Open questions

- Should a replacement vehicle be allowed to take over an active trip?
- How long should a finished trip remain locked to its last owner?
- Should `debug_dump.py` keep raw matches or only final owned matches?
