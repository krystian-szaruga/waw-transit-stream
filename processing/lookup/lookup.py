from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from processing.model import Trip, TripKey, TripGeometry, Lookup, VehicleType, M_PER_DEG
from core.repository import ReadRepository


class _TripLoader:
    def __init__(self, repository: ReadRepository):
        self._repository = repository

    def read(self) -> pd.DataFrame:
        return self._repository.load(self._payload_provider())

    @staticmethod
    def _payload_provider():
        return [
            (d := datetime.now(ZoneInfo("Europe/Warsaw")).date()) - timedelta(days=1), d, d + timedelta(days=1)
        ]


class _LookupBuilder:
    class _Col(StrEnum):
        SERVICE_DATE = "service_date"
        VEHICLE_TYPE = "vehicle_type"
        LINE = "line"
        BRIGADE = "brigade"
        ROUTE_ID = "route_id"
        TRIP_ID = "trip_id"
        STOP_ID = "stop_id"
        STOP_NAME = "stop_name"
        STOP_SEQUENCE = "stop_sequence"
        STOP_LAT = "stop_lat"
        STOP_LON = "stop_lon"
        SCHEDULED_ARRIVAL_OFFSET = "scheduled_arrival_offset"
        # computed by the builder
        X = "x"
        Y = "y"

    _TRIP_COLS = [_Col.SERVICE_DATE, _Col.TRIP_ID]
    _SORT_COLS = [_Col.SERVICE_DATE, _Col.TRIP_ID, _Col.STOP_SEQUENCE]

    def __init__(self, df: pd.DataFrame, lat0: float = 52.23) -> None:
        self._df = df
        self._k = float(np.cos(np.radians(lat0)))
        self._geometries: dict[bytes, TripGeometry] = {}

    def build(self) -> Lookup:
        df = self._project(self._sort(self._df))
        groups = df.groupby(self._TRIP_COLS, sort=False)

        lookup = Lookup(k=self._k)
        lookup.extend(self._to_trip(stops) for _, stops in groups)
        self._geometries.clear()
        return lookup

    def _sort(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.sort_values(by=self._SORT_COLS)

    def _project(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.assign(**{
            self._Col.X: df[self._Col.STOP_LON] * self._k * M_PER_DEG,
            self._Col.Y: df[self._Col.STOP_LAT] * M_PER_DEG,
        })

    def _to_trip(self, stops: pd.DataFrame) -> Trip:
        off = stops[self._Col.SCHEDULED_ARRIVAL_OFFSET].to_numpy()
        first = stops.iloc[0]
        xy = stops[[self._Col.X, self._Col.Y]].to_numpy()
        return Trip(
            key=TripKey(
                first[self._Col.SERVICE_DATE],
                VehicleType(int(first[self._Col.VEHICLE_TYPE])),
                first[self._Col.LINE],
                first[self._Col.BRIGADE],
            ),
            trip_id=first[self._Col.TRIP_ID],
            route_id=first[self._Col.ROUTE_ID],
            start=int(off.min()),
            end=int(off.max()),
            xy=xy,
            off=off,
            stop_id=stops[self._Col.STOP_ID].to_numpy(),
            stop_name=stops[self._Col.STOP_NAME].to_numpy(),
            seq=stops[self._Col.STOP_SEQUENCE].to_numpy(),
            geom=self._trip_geometry(xy),
            off_delta=np.diff(off),
        )

    def _trip_geometry(self, xy: np.ndarray) -> TripGeometry:
        key = xy.tobytes()
        geometry = self._geometries.get(key)
        if geometry is not None:
            return geometry

        a = xy[:-1]
        d = xy[1:] - a
        len2 = (d ** 2).sum(axis=1)
        seg_len = np.sqrt(len2)
        seg_idx = np.arange(len(d))
        geometry = TripGeometry(
            a=a,
            d=d,
            len2=len2,
            seg_len=seg_len,
            seg_len_cum=np.concatenate(([0.0], np.cumsum(seg_len))),
            seg_idx=seg_idx,
            seg_pos=seg_idx > 0,
            first_xy=(float(xy[0, 0]), float(xy[0, 1])),
            bbox=(
                float(xy[:, 0].min()),
                float(xy[:, 1].min()),
                float(xy[:, 0].max()),
                float(xy[:, 1].max()),
            ),
        )
        self._geometries[key] = geometry
        return geometry


class LookupLoader:
    def __init__(self, repository: ReadRepository):
        self._builder = _LookupBuilder(_TripLoader(repository).read())

    def load(self) -> Lookup:
        return self._builder.build()