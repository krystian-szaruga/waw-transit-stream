import argparse
import logging
import time

from core import ResourceState, timed
from database.timetable.state import create_state_repository
from database import create_timetable_writer
from gtfs.loader import TimetableLoader
from gtfs.loader.builder import GtfsFeed
from gtfs.request import WarsawGtfsDownloader

logger = logging.getLogger(__name__)


def run_once() -> int | None:
    state = create_state_repository()
    cached = state.get()
    downloaded = WarsawGtfsDownloader().download(cached.etag, cached.last_modified)
    if downloaded is None:
        return None
    version_id = TimetableLoader(create_timetable_writer()).run(
        GtfsFeed.from_zip(downloaded.content), downloaded.sha256
    )
    state.put(ResourceState(downloaded.etag, downloaded.last_modified))
    return version_id


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=1800)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    while True:
        with timed("download + load"):
            version_id = run_once()
        if version_id is None:
            logger.info("Feed unchanged")
        else:
            logger.info("Timetable version %d active", version_id)
        if not args.watch:
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
