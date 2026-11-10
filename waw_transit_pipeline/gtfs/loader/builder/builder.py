import io
import zipfile
from dataclasses import dataclass
from datetime import date, timedelta
from enum import IntEnum
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class GtfsFeed:
    routes: pd.DataFrame
    trips: pd.DataFrame
    stop_times: pd.DataFrame
    stops: pd.DataFrame
    shapes: pd.DataFrame
    calendar_dates: pd.DataFrame

    @classmethod
    def from_directory(cls, directory: str | Path) -> "GtfsFeed":
        d = Path(directory)
        return cls(
            routes=pd.read_csv(
                d / "routes.txt", dtype=str,
                usecols=["route_id", "route_short_name", "route_type"],
            ),
            trips=pd.read_csv(
                d / "trips.txt", dtype=str,
                usecols=["route_id", "service_id", "trip_id", "block_short_name", "shape_id"],
            ),
            stop_times=pd.read_csv(
                d / "stop_times.txt",
                usecols=["trip_id", "stop_id", "stop_sequence", "arrival_time"],
                dtype={"trip_id": str, "stop_id": str, "stop_sequence": "int32"},
            ),
            stops=pd.read_csv(
                d / "stops.txt",
                usecols=["stop_id", "stop_name", "stop_lat", "stop_lon"],
                dtype={"stop_id": str},
            ),
            shapes=pd.read_csv(
                d / "shapes.txt",
                usecols=["shape_id", "shape_pt_sequence", "shape_pt_lat", "shape_pt_lon"],
                dtype={"shape_id": str, "shape_pt_sequence": "int32"},
            ),
            calendar_dates=pd.read_csv(
                d / "calendar_dates.txt", dtype=str,
                usecols=["service_id", "date", "exception_type"],
            ),
        )

    @classmethod
    def from_zip(cls, content: bytes) -> "GtfsFeed":
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            def read(name: str, **kwargs) -> pd.DataFrame:
                return pd.read_csv(archive.open(name), **kwargs)

            return cls(
                routes=read(
                    "routes.txt", dtype=str,
                    usecols=["route_id", "route_short_name", "route_type"],
                ),
                trips=read(
                    "trips.txt", dtype=str,
                    usecols=["route_id", "service_id", "trip_id", "block_short_name", "shape_id"],
                ),
                stop_times=read(
                    "stop_times.txt",
                    usecols=["trip_id", "stop_id", "stop_sequence", "arrival_time"],
                    dtype={"trip_id": str, "stop_id": str, "stop_sequence": "int32"},
                ),
                stops=read(
                    "stops.txt",
                    usecols=["stop_id", "stop_name", "stop_lat", "stop_lon"],
                    dtype={"stop_id": str},
                ),
                shapes=read(
                    "shapes.txt",
                    usecols=["shape_id", "shape_pt_sequence", "shape_pt_lat", "shape_pt_lon"],
                    dtype={"shape_id": str, "shape_pt_sequence": "int32"},
                ),
                calendar_dates=read(
                    "calendar_dates.txt", dtype=str,
                    usecols=["service_id", "date", "exception_type"],
                ),
            )


class TimetableBuilder:
    COLUMNS = [
        "service_date", "vehicle_type", "line", "brigade", "route_id", "trip_id",
        "stop_id", "stop_name", "stop_sequence", "stop_lat", "stop_lon", "scheduled_arrival_offset",
    ]

    class _VehicleType(IntEnum):
        BUS = 1
        TRAM = 2

        @property
        def gtfs_route_type(self) -> int:
            return 3 if self is type(self).BUS else 0

    def __init__(
        self,
        feed: GtfsFeed,
        service_dates: list[date],
        vehicle_types: tuple[_VehicleType, ...] = (_VehicleType.BUS, _VehicleType.TRAM),
    ):
        self._feed = feed
        self._service_dates = service_dates
        self._vehicle_types = vehicle_types

    @classmethod
    def for_today_and_tomorrow(cls, feed: GtfsFeed, today: date | None = None) -> "TimetableBuilder":
        today = today or date.today()
        return cls(feed, [today, today + timedelta(days=1)])

    def build(self) -> pd.DataFrame:
        trips = self._active_trips().merge(self._routes(), on="route_id", validate="m:1")
        timetable = (
            trips
            .merge(self._stop_times(trips["trip_id"]), on="trip_id")
            .merge(self._feed.stops, on="stop_id", validate="m:1")
        )
        return timetable[self.COLUMNS].reset_index(drop=True)

    @staticmethod
    def time_to_offset(times: pd.Series) -> pd.Series:
        unique = pd.Series(times.unique())
        parts = unique.str.strip().str.split(":", expand=True).astype(int)
        lookup = dict(zip(unique, parts[0] * 3600 + parts[1] * 60 + parts[2]))
        return times.map(lookup)

    def _active_services(self) -> pd.DataFrame:
        cal = self._feed.calendar_dates
        cal = cal[cal["exception_type"] == "1"].assign(
            service_date=lambda d: pd.to_datetime(d["date"], format="%Y%m%d").dt.date
        )
        return cal[cal["service_date"].isin(self._service_dates)][
            ["service_id", "service_date"]
        ].drop_duplicates()

    def _active_trips(self) -> pd.DataFrame:
        return (
            self._feed.trips
            .merge(self._active_services(), on="service_id")
            .rename(columns={"block_short_name": "brigade"})
            .drop(columns="service_id")
        )

    def _routes(self) -> pd.DataFrame:
        gtfs_to_vehicle = {vt.gtfs_route_type: int(vt) for vt in self._vehicle_types}
        routes = self._feed.routes.assign(route_type=lambda d: d["route_type"].astype(int))
        routes = routes[routes["route_type"].isin(gtfs_to_vehicle)]
        return routes.assign(
            vehicle_type=routes["route_type"].map(gtfs_to_vehicle),
            line=routes["route_short_name"],
        )[["route_id", "vehicle_type", "line"]]

    def _stop_times(self, trip_ids: pd.Series) -> pd.DataFrame:
        st = self._feed.stop_times
        st = st[st["trip_id"].isin(trip_ids)]
        return st.assign(
            scheduled_arrival_offset=self.time_to_offset(st["arrival_time"])
        ).drop(columns="arrival_time")


class ShapeBuilder:
    TRIP_COLUMNS = ["trip_id", "shape_id"]
    POINT_COLUMNS = ["shape_id", "point_sequence", "lat", "lon"]

    def __init__(self, feed: GtfsFeed) -> None:
        self._feed = feed

    def build(self, trip_ids: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
        trips = self._trip_shapes(trip_ids)
        return trips, self._shape_points(trips["shape_id"].unique())

    def _trip_shapes(self, trip_ids: pd.Series) -> pd.DataFrame:
        trips = self._feed.trips
        present = trips["trip_id"].isin(set(trip_ids)) & trips["shape_id"].notna()
        return (
            trips.loc[present, self.TRIP_COLUMNS]
            .drop_duplicates("trip_id")
            .sort_values("trip_id", ignore_index=True)
        )

    def _shape_points(self, shape_ids) -> pd.DataFrame:
        shapes = self._feed.shapes
        selected = shapes[shapes["shape_id"].isin(set(shape_ids))]
        return (
            selected.assign(
                point_sequence=selected["shape_pt_sequence"],
                lat=selected["shape_pt_lat"].astype("float32"),
                lon=selected["shape_pt_lon"].astype("float32"),
            )[self.POINT_COLUMNS]
            .sort_values(["shape_id", "point_sequence"], ignore_index=True)
        )
