import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from waw_transit_pipeline.gtfs.loader.builder import GtfsFeed


@pytest.fixture
def feed_frames() -> dict[str, pd.DataFrame]:
    return {
        "routes": pd.DataFrame(
            {
                "route_id": ["R-BUS", "R-TRAM", "R-RAIL"],
                "route_short_name": ["175", "9", "S1"],
                "route_type": ["3", "0", "2"],
                "route_color": ["red", "blue", "green"],
            }
        ),
        "trips": pd.DataFrame(
            {
                "route_id": ["R-BUS", "R-TRAM", "R-BUS", "R-RAIL", "R-BUS"],
                "service_id": ["S-WEEKDAY", "S-WEEKDAY", "S-REMOVED", "S-WEEKDAY", "S-TOMORROW"],
                "trip_id": ["T-BUS-1", "T-TRAM-1", "T-BUS-REMOVED", "T-RAIL", "T-BUS-2"],
                "block_short_name": ["B1", "B2", "B3", "B4", "B5"],
                "trip_headsign": ["Centrum", "Dw. Wileński", "Nowhere", "S1", "Centrum"],
                "shape_id": ["SH-BUS-1", "SH-TRAM-1", "SH-REMOVED", "SH-RAIL", "SH-BUS-2"],
            }
        ),
        "stop_times": pd.DataFrame(
            {
                "trip_id": [
                    "T-BUS-1", "T-BUS-1", "T-BUS-1",
                    "T-TRAM-1", "T-BUS-REMOVED", "T-RAIL",
                    "T-BUS-2", "T-BUS-2",
                ],
                "stop_id": ["1001", "1002", "1001", "2001", "1001", "1001", "1001", "1002"],
                "stop_sequence": [1, 2, 3, 1, 1, 1, 1, 2],
                "arrival_time": [
                    "07:00:00", "07:10:00", "25:05:00",
                    "08:00:00", "09:00:00", "10:00:00",
                    "07:00:00", "07:20:00",
                ],
                "pickup_type": [0, 0, 0, 0, 0, 0, 0, 0],
            }
        ),
        "stops": pd.DataFrame(
            {
                "stop_id": ["1001", "1002", "2001"],
                "stop_name": ["Plac Zawiszy", "Centrum", "Most Poniatowskiego"],
                "stop_lat": [52.2301, 52.2310, 52.2400],
                "stop_lon": [20.9901, 20.9910, 21.0300],
                "stop_desc": ["a", "b", "c"],
            }
        ),
        "shapes": pd.DataFrame(
            {
                "shape_id": [
                    "SH-BUS-1", "SH-BUS-1", "SH-BUS-1",
                    "SH-TRAM-1", "SH-TRAM-1",
                    "SH-BUS-2", "SH-BUS-2",
                    "SH-RAIL", "SH-REMOVED",
                ],
                "shape_pt_sequence": [2, 0, 1, 0, 1, 0, 1, 0, 0],
                "shape_pt_lat": [
                    52.2500, 52.2300, 52.2400,
                    52.2000, 52.2100,
                    52.2300, 52.2600,
                    52.1000, 52.3000,
                ],
                "shape_pt_lon": [
                    21.0100, 20.9900, 21.0000,
                    21.0000, 21.0100,
                    20.9900, 21.0200,
                    21.0000, 21.0500,
                ],
                "shape_dist_traveled": [3.0, 0.0, 1.5, 0.0, 1.0, 0.0, 2.0, 0.0, 0.0],
            }
        ),
        "calendar_dates": pd.DataFrame(
            {
                "service_id": ["S-WEEKDAY", "S-WEEKDAY", "S-TOMORROW", "S-REMOVED"],
                "date": ["20261104", "20261105", "20261105", "20261104"],
                "exception_type": ["1", "1", "1", "2"],
                "unused": ["x", "x", "x", "x"],
            }
        ),
    }

@pytest.fixture
def gtfs_feed(feed_frames) -> GtfsFeed:
    return GtfsFeed(
        routes=feed_frames["routes"].drop(columns=["route_color"]),
        trips=feed_frames["trips"].drop(columns=["trip_headsign"]),
        stop_times=feed_frames["stop_times"].drop(columns=["pickup_type"]),
        stops=feed_frames["stops"].drop(columns=["stop_desc"]),
        shapes=feed_frames["shapes"].drop(columns=["shape_dist_traveled"]),
        calendar_dates=feed_frames["calendar_dates"].drop(columns=["unused"]),
    )


@pytest.fixture
def gtfs_zip(feed_frames) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, frame in feed_frames.items():
            archive.writestr(f"{name}.txt", frame.to_csv(index=False))
    return buffer.getvalue()


@pytest.fixture
def gtfs_directory(feed_frames, tmp_path: Path) -> Path:
    directory = tmp_path / "gtfs"
    directory.mkdir()
    for name, frame in feed_frames.items():
        frame.to_csv(directory / f"{name}.txt", index=False)
    return directory
