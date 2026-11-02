import logging

from core import timed
from database import create_timetable_repository
from loader import TimetableLoader
from topology.request.request import WarsawGtfsDownloader

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    with timed("total"):
        with timed("download"):
            feed_dir = WarsawGtfsDownloader(target_dir="data").download()
        loader = TimetableLoader(create_timetable_repository())
        with timed("load (read csv + build + save)"):
            loaded = loader.run(feed_dir)
        logger.info("Loaded %d timetable rows", loaded)


if __name__ == "__main__":
    main()