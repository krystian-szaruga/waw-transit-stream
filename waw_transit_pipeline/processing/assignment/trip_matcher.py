from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from typing import Iterator

import numpy as np
import pandas as pd

from waw_transit_pipeline.processing.model import Lookup, MatchStatus, TripMatchCol, WarsawLiveCol
from waw_transit_pipeline.processing.assignment.records import Anchor, Match, MatchState, Trip, VehicleType


class TripMatcher:
    def __init__(self, lookup: Lookup, version_id: int) -> None:
        self._lookup = lookup
        self._config = _Config()
        self._direction = _Direction(self._config)
        self._candidates = _CandidateFinder(lookup, self._config)
        self._choice = _Choice(self._candidates, self._config)
        self._rows = _Rows(self._config, version_id)

    def match_rows(
            self,
            pdf: pd.DataFrame,
            state: MatchState,
    ) -> tuple[tuple | None, datetime | None, MatchState]:
        feed = _PingFeed(pdf)
        if not feed.pings:
            return None, None, state
        matches, new_state = self._run(feed.pings, state)
        return self._rows.row(matches[-1], feed.pings[-1]), feed.pings[-1].ts, new_state

    def _run(
            self,
            pings: list[_LivePing],
            state: MatchState,
    ) -> tuple[list[Match | None], MatchState]:
        incumbent, anchor = state.incumbent, state.anchor
        matches: list[Match | None] = []
        for ping in pings:
            x, y = self._lookup.project(ping.lon, ping.lat)
            heading = self._direction.heading(anchor, x, y, ping.ts)
            match = self._choice.choose(ping, x, y, incumbent, heading)
            incumbent = match.trip.trip_id if match is not None else None
            anchor = self._direction.next_anchor(anchor, x, y, ping.ts, heading)
            matches.append(match)

        return matches, replace(state, incumbent=incumbent, anchor=anchor)


class _PingFeed:
    def __init__(self, pdf: pd.DataFrame) -> None:
        self._frame = pdf.drop_duplicates(subset=[WarsawLiveCol.TIME])
        pings = self._pings(self._frame)
        self._order = sorted(range(len(pings)), key=lambda i: pings[i].ts)
        self._sorted = [pings[i] for i in self._order]

    @property
    def frame(self) -> pd.DataFrame:
        return self._frame

    @property
    def pings(self) -> list[_LivePing]:
        return self._sorted

    @property
    def order(self) -> list[int]:
        return self._order

    @staticmethod
    def _pings(pdf: pd.DataFrame) -> list[_LivePing]:
        times = pdf[WarsawLiveCol.TIME]
        if not pd.api.types.is_datetime64_any_dtype(times):
            pdf = pdf.assign(**{WarsawLiveCol.TIME.value: pd.to_datetime(times)})
        return [
            _LivePing(VehicleType(int(vt)), number, line, brigade, lon, lat, ts)
            for vt, number, line, brigade, lon, lat, ts
            in zip(
                pdf[WarsawLiveCol.VEHICLE_TYPE].tolist(),
                pdf[WarsawLiveCol.VEHICLE_NUMBER].tolist(),
                pdf[WarsawLiveCol.LINE].tolist(),
                pdf[WarsawLiveCol.BRIGADE].tolist(),
                pdf[WarsawLiveCol.LON].tolist(),
                pdf[WarsawLiveCol.LAT].tolist(),
                pdf[WarsawLiveCol.TIME].tolist(),
            )
        ]


class _Direction:
    def __init__(self, config: _Config) -> None:
        self._config = config

    def heading(self, anchor: Anchor | None, x: float, y: float, ts: datetime) -> tuple[float, float] | None:
        if anchor is None:
            return None
        ax, ay, ats = anchor
        if (ts - ats).total_seconds() > self._config.max_anchor_age_sec:
            return None
        dx, dy = x - ax, y - ay
        if np.hypot(dx, dy) < self._config.min_move_m:
            return None
        return dx, dy

    def next_anchor(
            self,
            anchor: Anchor | None,
            x: float,
            y: float,
            ts: datetime,
            heading: tuple[float, float] | None,
    ) -> Anchor:
        if anchor is None or heading is not None:
            return x, y, ts
        if (ts - anchor[2]).total_seconds() > self._config.max_anchor_age_sec:
            return x, y, ts
        return anchor


class _CandidateFinder:
    def __init__(self, lookup: Lookup, config: _Config) -> None:
        self._lookup = lookup
        self._config = config

    def find(
            self,
            ping: _LivePing,
            x: float,
            y: float,
            heading: tuple[float, float] | None = None,
    ) -> Iterator[Match]:
        projections: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        for service_date in ping.service_dates():
            sec = ping.seconds_since_midnight(service_date)
            for trip in self._active_trips(ping, service_date, sec):
                if fit := self._fit(trip, x, y, sec, heading, projections):
                    yield fit

    def _active_trips(self, ping: _LivePing, service_date: date, sec: float) -> list[Trip]:
        return self._lookup.active_trips(
            service_date,
            ping.vehicle_type,
            ping.line,
            sec,
            0.0,
            self._config.post_end_grace_sec,
        )

    def _fit(
            self,
            trip: Trip,
            x: float,
            y: float,
            sec: float,
            heading: tuple[float, float] | None = None,
            projections: dict[int, tuple[np.ndarray, np.ndarray]] | None = None,
    ) -> Match | None:
        cfg = self._config
        geom = trip.geom
        min_x, min_y, max_x, max_y = geom.bbox
        if x < min_x - cfg.max_dist_m or x > max_x + cfg.max_dist_m:
            return None
        if y < min_y - cfg.max_dist_m or y > max_y + cfg.max_dist_m:
            return None

        first_x, first_y = geom.first_xy
        first_stop_dist = np.hypot(x - first_x, y - first_y)
        if first_stop_dist <= cfg.max_dist_m and sec - trip.start > cfg.max_start_delay_sec:
            return None

        key = id(geom)
        projection = None if projections is None else projections.get(key)
        if projection is None:
            a, d = geom.a, geom.d
            t = np.divide(
                (x - a[:, 0]) * d[:, 0] + (y - a[:, 1]) * d[:, 1],
                geom.len2, out=np.zeros_like(geom.len2), where=geom.len2 > 0,
            ).clip(0.0, 1.0)
            dist = np.hypot(x - (a[:, 0] + t * d[:, 0]), y - (a[:, 1] + t * d[:, 1]))
            projection = (t, dist)
            if projections is not None:
                projections[key] = projection
        else:
            t, dist = projection

        delay = sec - (trip.off[:-1] + t * trip.off_delta)
        seg = geom.seg_idx
        delay_cost = np.where((delay < 0) & geom.seg_pos, -delay * cfg.early_penalty, np.abs(delay))
        cost = dist + cfg.delay_weight * delay_cost

        if heading is not None:
            hx, hy = heading
            denom = geom.seg_len * np.hypot(hx, hy)
            cos = np.divide(
                geom.d[:, 0] * hx + geom.d[:, 1] * hy,
                denom,
                out=np.zeros_like(denom), where=denom > 0,
            )
            cost = cost + np.where(cos < cfg.wrong_way_cos, cfg.wrong_way_penalty, 0.0)

        at_first_stop = (seg == 0) & (t < 0.05)
        early_tol = np.where(at_first_stop, cfg.layover_tol_sec, cfg.early_tol_sec)
        late_tol = np.where(seg == 0, cfg.max_start_delay_sec, cfg.late_tol_sec)
        plausible = (delay >= -early_tol) & (delay <= late_tol) & (dist <= cfg.max_dist_m)
        if sec < trip.start:
            return None
        if not plausible.any():
            return None

        cost = np.where(plausible, cost, np.inf)

        i = int(np.argmin(cost))
        finished = i == len(delay) - 1 and t[i] >= cfg.finish_frac
        traveled = geom.seg_len_cum[i] + t[i] * geom.seg_len[i]
        if sec > trip.end and traveled < cfg.post_end_min_progress * geom.seg_len_cum[-1]:
            return None
        return Match(trip, float(dist[i]), float(delay[i]), float(cost[i]), finished, i, float(t[i]))


class _Choice:
    def __init__(self, candidates: _CandidateFinder, config: _Config) -> None:
        self._candidates = candidates
        self._config = config

    def choose(
            self,
            ping: _LivePing,
            x: float,
            y: float,
            incumbent: str | None = None,
            heading: tuple[float, float] | None = None,
    ) -> Match | None:
        candidates = list(self._candidates.find(ping, x, y, heading))
        if not candidates:
            return None

        held = next((m for m in candidates if m.trip.trip_id == incumbent), None)
        pool = [m for m in candidates if m.trip.trip_id != incumbent]
        best_other = min(pool, key=lambda m: m.cost) if pool else None

        if held is not None and not held.finished:
            if held.delay_sec > 720 and best_other is not None and best_other.cost < held.cost:
                return best_other

            if best_other is None or held.cost <= best_other.cost + self._config.switch_margin:
                return held
            return best_other

        return best_other or held


class _Rows:
    def __init__(self, config: _Config, version_id: int) -> None:
        self._config = config
        self._version_id = version_id

    def row(self, match: Match | None, ping: _LivePing) -> tuple:
        if match is None:
            return (
                int(ping.vehicle_type), ping.vehicle_number, ping.brigade, ping.line,
                None, None, None, None, MatchStatus.UNMATCHED, ping.ts, self._version_id,
                ping.lon, ping.lat, None,
            )
        status = MatchStatus.LAYOVER if self._is_layover(match) else MatchStatus.MATCHED
        return (
            int(ping.vehicle_type), ping.vehicle_number, ping.brigade, ping.line,
            match.trip.trip_id, match.dist_m, match.delay_sec, match.cost, status, ping.ts,
            self._version_id, ping.lon, ping.lat, int(match.trip.seq[match.seg + 1]),
        )

    def frame(self, pdf: pd.DataFrame, pings: list[_LivePing], matches: list[Match | None]) -> pd.DataFrame:
        matched = pd.DataFrame(
            [m.as_row() if m else Match.no_match_row() for m in matches],
            columns=[
                TripMatchCol.TRIP_ID,
                TripMatchCol.DIST_M,
                TripMatchCol.DELAY_SEC,
                TripMatchCol.COST,
            ],
            index=pdf.index,
        )
        matched[TripMatchCol.API_TS] = pd.to_datetime([p.ts for p in pings]).values
        matched[TripMatchCol.MATCH_STATUS] = pd.Series(
            [
                MatchStatus.UNMATCHED if m is None
                else MatchStatus.LAYOVER if self._is_layover(m)
                else MatchStatus.MATCHED
                for m in matches
            ],
            index=pdf.index,
            dtype="string",
        )
        matched[TripMatchCol.VEHICLE_TYPE] = pdf[WarsawLiveCol.VEHICLE_TYPE].astype("int32")
        matched[TripMatchCol.VEHICLE_NUMBER] = pdf[WarsawLiveCol.VEHICLE_NUMBER]
        matched[TripMatchCol.BRIGADE] = pdf[WarsawLiveCol.BRIGADE]
        matched[TripMatchCol.LINE] = pdf[WarsawLiveCol.LINE]
        matched[TripMatchCol.GTFS_VERSION] = self._version_id
        matched[TripMatchCol.TRIP_ID] = matched[TripMatchCol.TRIP_ID].astype("string")
        for column in (TripMatchCol.DIST_M, TripMatchCol.DELAY_SEC, TripMatchCol.COST):
            matched[column] = matched[column].astype("float64")
        return matched[[c.value for c in TripMatchCol]]

    def _is_layover(self, match: Match) -> bool:
        return (
            match.seg == 0
            and match.t < 0.05
            and match.delay_sec <= self._config.waiting_tol_sec
        )


@dataclass(slots=True, frozen=True)
class _LivePing:
    vehicle_type: VehicleType
    vehicle_number: str
    line: str
    brigade: str
    lon: float
    lat: float
    ts: datetime

    def seconds_since_midnight(self, service_date: date) -> float:
        return (self.ts - datetime.combine(service_date, time.min)).total_seconds()

    def service_dates(self) -> list[date]:
        return [self.ts.date(), self.ts.date() - timedelta(days=1)]


@dataclass(frozen=True, slots=True)
class _Config:
    early_tol_sec: int = 600      # how early before the start a trip becomes a candidate
    late_tol_sec: int = 900       # max allowed lateness; above this the ping stays unmatched
    post_end_grace_sec: int = 600
    post_end_min_progress: float = 0.1
    waiting_tol_sec: int = 1200
    max_dist_m: float = 200.0
    delay_weight: float = 1.0
    early_penalty: float = 3.0    # being early away from the first stop is implausible
    finish_frac: float = 0.98     # position on the last segment >= this -> trip finished
    switch_margin: float = 300.0
    max_start_delay_sec: int = 900
    layover_tol_sec: int = 600
    min_move_m: float = 10.0           # smaller displacement is GPS noise, not a heading
    max_anchor_age_sec: int = 120      # older anchor is too stale to give a direction
    wrong_way_cos: float = -0.3        # cos(angle) below this = segment points the opposite way
    wrong_way_penalty: float = 1000.0  # must stay > switch_margin (300)
