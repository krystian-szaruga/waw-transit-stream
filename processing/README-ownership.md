# Trip ownership: one vehicle, several trips

## Summary

Nothing in the current implementation prevents a single vehicle from being the
owner of more than one trip at the same time.

## Where the assignment happens

- `TripMatcher.match_batch` produces, per vehicle, the single best trip for the
  latest ping. It has no knowledge of other vehicles.
- `TripOwnership.resolve` then ranks candidates per `trip_id`:
  `_TripLoop.winners` iterates `candidates.groupby(TRIP_ID)` and calls
  `_TripRanker.choice`, which picks the cheapest vehicle **for that trip only**.
- `_TripRanker._ranked` drops duplicate vehicles within one trip group, but
  there is no constraint across trips.

## The only guard, and why it is not enough

`_TripLoop.winners` keeps a local `claimed` set and skips vehicles that already
won a trip **in the same micro-batch**. That set is created per call and thrown
away afterwards.

Consequences:

- within one batch, a vehicle wins at most one trip,
- across batches, nothing stops the same vehicle from being recorded as the owner
  of another trip, because ownership lives in `_OwnerStore` keyed by `trip_id`
  and there is no reverse index (vehicle -> trip),
- a previously recorded ownership stays in the store until `_OwnerStore.retain`
  drops it (`trip.end + ttl_sec`, `ttl_sec = 300` s).

## Observed impact

Example from dumps (2026-11-03, line 314, vehicle 1046, 14:35:15, two rows with
the same `api_timestamp`):

| trip_id | delay_sec | note |
| --- | --- | --- |
| `2026-11-03:314:PcS:2:1334` | 635 s | own brigade |
| `2026-11-03:314:PcS:1:1414` | 1199 s | other brigade |

Effects:

- delay statistics are taken over rows, not vehicles, so the extra assignment
  shows up as a 20-minute delay,
- a trip is held by a vehicle that is actually running a different trip, so a
  better vehicle cannot take it,
- the output is not one row per vehicle, and downstream consumers must not
  assume that it is.

## What does not help

- Brigade cannot be used as a hard filter: the source API reports trips under a
  brigade that does not always match the vehicle's brigade, so filtering would
  drop valid assignments.
- Time and distance limits do not cover this case: every single assignment is
  plausible on its own, only the combination is wrong.

## Current status

The limitation is not fixed. A complete fix needs per-vehicle ownership
(vehicle -> trip) that is consulted across batches, not a per-batch set.
