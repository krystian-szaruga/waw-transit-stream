import logging

from core import timed
from database import create_timetable_writer
from loader import TimetableLoader
from loader.builder import GtfsFeed
from request import WarsawGtfsDownloader

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    with timed("total"):
        with timed("download"):
            content = WarsawGtfsDownloader().download()
        loader = TimetableLoader(create_timetable_writer())
        with timed("load (read zip + build + save)"):
            loaded = loader.run(GtfsFeed.from_zip(content))
        logger.info("Loaded %d timetable rows", loaded)


if __name__ == "__main__":
    main()