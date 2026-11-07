from __future__ import annotations

import argparse
import logging

from waw_transit.database import create_timetable_writer
from waw_transit.database.postgres.repository.feed_state import create_state_repository
from waw_transit_pipeline.adapters.gtfs import create_gtfs_downloader
from waw_transit_pipeline.gtfs.loader import TimetableLoader
from waw_transit_pipeline.gtfs.sync import TimetableSync


def run_gtfs(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=1800)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    sync = TimetableSync(
        TimetableLoader(create_timetable_writer()),
        create_state_repository(),
        create_gtfs_downloader(),
        args.interval,
    )
    if args.watch:
        sync.watch()
    else:
        sync.run()


if __name__ == "__main__":
    run_gtfs()
