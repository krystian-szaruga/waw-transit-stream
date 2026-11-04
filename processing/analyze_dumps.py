import argparse
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from debug_dump import DUMP_DIR
from processing.model import MatchState, TripMatchCol
from processing.assignment.trip_matcher import TripMatcher


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=Path, default=DUMP_DIR)
    parser.add_argument("--top", type=int, default=25)
    parser.add_argument("--detail", type=int, default=10)
    args = parser.parse_args()

    cases = _load_cases(args.dir)
    if cases.empty:
        print(f"no cases in {args.dir}")
        return
    _summary(cases)
    _top_table(cases, args.top)

    lookup_path = args.dir / "lookup.pkl"
    if not lookup_path.exists():
        print(f"\nmissing {lookup_path}; skipping detailed replay")
        return

    with open(lookup_path, "rb") as handle:
        lookup = pickle.load(handle)
    matcher = TripMatcher(lookup)
    trips = _trip_dict(lookup)

    ordered = cases.sort_values(_col(TripMatchCol.DELAY_SEC), ascending=False).head(args.detail)
    for _, row in ordered.iterrows():
        _detail(args.dir, matcher, trips, row)


def _load_cases(dump_dir: Path) -> pd.DataFrame:
    frames = []
    for path in sorted(dump_dir.glob("*_matched.parquet")):
        frame = pd.read_parquet(path)
        if frame.empty:
            continue
        frame = frame.copy()
        frame["source"] = path.stem
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _summary(cases: pd.DataFrame) -> None:
    print(f"cases: {len(cases)}")
    print(f"dump dir: {cases['source'].iloc[0] if len(cases) else '-'}")

    by_line = (
        cases.groupby(_col(TripMatchCol.LINE))
        .agg(cases=(_col(TripMatchCol.TRIP_ID), "size"), max_delay=(_col(TripMatchCol.DELAY_SEC), "max"))
        .sort_values("cases", ascending=False)
    )
    print("\nby line")
    print(by_line.to_string())

    trip_vehicles = cases.groupby(_col(TripMatchCol.TRIP_ID))[_col(TripMatchCol.VEHICLE_NUMBER)].nunique()
    print("\ntrips matched to more than one vehicle")
    print(trip_vehicles[trip_vehicles > 1].sort_values(ascending=False).head(30).to_string())

    vehicle_trips = cases.groupby(_col(TripMatchCol.VEHICLE_NUMBER))[_col(TripMatchCol.TRIP_ID)].nunique()
    print("\nvehicles matched to more than one trip")
    print(vehicle_trips[vehicle_trips > 1].sort_values(ascending=False).head(30).to_string())


def _top_table(cases: pd.DataFrame, top: int) -> None:
    columns = [
        _col(TripMatchCol.API_TS),
        _col(TripMatchCol.LINE),
        _col(TripMatchCol.BRIGADE),
        _col(TripMatchCol.VEHICLE_NUMBER),
        _col(TripMatchCol.TRIP_ID),
        _col(TripMatchCol.DELAY_SEC),
        _col(TripMatchCol.DIST_M),
        "source",
    ]
    ordered = cases.sort_values(_col(TripMatchCol.DELAY_SEC), ascending=False).head(top)
    print(f"\ntop {top} by delay")
    print(ordered[columns].to_string(index=False))


def _trip_dict(lookup) -> dict[str, object]:
    return {trip.trip_id: trip for trip in lookup}


def _detail(dump_dir: Path, matcher: TripMatcher, trips: dict[str, object], row: pd.Series) -> None:
    source = str(row["source"])
    raw_path = dump_dir / f"{source.removesuffix('_matched')}.parquet"
    print("\n" + "=" * 120)
    print(source)
    if not raw_path.exists():
        print(f"missing raw file: {raw_path}")
        return

    raw = pd.read_parquet(raw_path).sort_values("Time")
    print(raw.to_string(index=False))

    pings = matcher._pings(raw)
    if not pings:
        return
    ping = pings[-1]

    if len(pings) > 1:
        xy = np.array([matcher._lookup.project(p.lon, p.lat) for p in pings])
        elapsed = (pings[-1].ts - pings[0].ts).total_seconds()
        shift = float(np.hypot(*(xy[-1] - xy[0])))
        print(
            f"history: pings={len(pings)} span={elapsed:.0f}s displacement={shift:.1f}m "
            f"mean_speed={shift / elapsed if elapsed > 0 else 0.0:.2f}m/s"
        )

    matched, _ = matcher.match_batch(raw, MatchState())
    print("\nreplay")
    print(
        matched[[
            _col(TripMatchCol.API_TS),
            _col(TripMatchCol.TRIP_ID),
            _col(TripMatchCol.DELAY_SEC),
            _col(TripMatchCol.DIST_M),
            _col(TripMatchCol.MATCH_STATUS),
        ]].to_string(index=False)
    )

    chosen = trips.get(str(row[_col(TripMatchCol.TRIP_ID)]))
    if chosen is not None:
        print(
            f"\nchosen trip: {chosen.trip_id} start={chosen.start} end={chosen.end} "
            f"{chosen.stop_name[0]} -> {chosen.stop_name[-1]}"
        )

    candidates = _candidate_rows(matcher, ping)
    if candidates.empty:
        print("no candidates for the last ping")
        return
    candidates = candidates.sort_values("seg_dist")
    print("\ncandidates for the last ping")
    print(candidates.to_string(index=False))


def _candidate_rows(matcher, ping) -> pd.DataFrame:
    lookup = matcher._lookup
    cfg = matcher._config
    x, y = lookup.project(ping.lon, ping.lat)
    rows = []
    for service_date in ping.service_dates():
        sec = ping.seconds_since_midnight(service_date)
        for trip in matcher._active_trips(ping, service_date, sec):
            a, b = trip.xy[:-1], trip.xy[1:]
            d = b - a
            len2 = (d ** 2).sum(axis=1)
            t = np.divide(
                (x - a[:, 0]) * d[:, 0] + (y - a[:, 1]) * d[:, 1],
                len2,
                out=np.zeros_like(len2),
                where=len2 > 0,
            ).clip(0.0, 1.0)
            dist = np.hypot(x - (a[:, 0] + t * d[:, 0]), y - (a[:, 1] + t * d[:, 1]))
            delay = sec - (trip.off[:-1] + t * (trip.off[1:] - trip.off[:-1]))
            idx = int(np.argmin(dist))
            vertex = int(np.argmin(np.hypot(trip.xy[:, 0] - x, trip.xy[:, 1] - y)))
            fit = matcher._fit(trip, x, y, sec)
            rows.append({
                "trip_id": trip.trip_id,
                "first_stop": trip.stop_name[0],
                "last_stop": trip.stop_name[-1],
                "trip_start": trip.start,
                "trip_end": trip.end,
                "ended_before_ping": trip.end < sec,
                "nearest_stop": trip.stop_name[vertex],
                "vertex_dist": round(float(np.hypot(trip.xy[vertex, 0] - x, trip.xy[vertex, 1] - y)), 1),
                "seg_dist": round(float(dist[idx]), 1),
                "seg_delay": round(float(delay[idx]), 1),
                "seg": idx,
                "fit": fit is not None,
                "fit_dist": None if fit is None else round(fit.dist_m, 1),
                "fit_delay": None if fit is None else round(fit.delay_sec, 1),
                "fit_cost": None if fit is None else round(fit.cost, 1),
                "max_dist": cfg.max_dist_m,
            })
    return pd.DataFrame(rows)


def _col(name: TripMatchCol) -> str:
    return name.value


if __name__ == "__main__":
    _main()
