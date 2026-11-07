import logging
import time
from contextlib import contextmanager
from typing import Iterator

from waw_transit.core import ResourceState, ResourceStateRepository
from waw_transit_pipeline.core.ports import GtfsDownloader
from waw_transit_pipeline.gtfs.loader import TimetableLoader
from waw_transit_pipeline.gtfs.loader.builder import GtfsFeed

logger = logging.getLogger(__name__)


class TimetableSync:
    def __init__(
        self,
        loader: TimetableLoader,
        state: ResourceStateRepository,
        downloader: GtfsDownloader,
        interval: int = 1800,
    ) -> None:
        self._loader = loader
        self._state = state
        self._downloader = downloader
        self._interval = interval

    def run(self) -> None:
        with timed("download + load"):
            version_id = self._run_once()
        self._log(version_id)

    def watch(self) -> None:
        while True:
            self.run()
            time.sleep(self._interval)

    def _run_once(self) -> int | None:
        cached = self._state.get()
        downloaded = self._downloader.download(cached.etag, cached.last_modified)
        if downloaded is None:
            return None
        version_id = self._loader.run(
            GtfsFeed.from_zip(downloaded.content), downloaded.sha256
        )
        self._state.put(ResourceState(downloaded.etag, downloaded.last_modified))
        return version_id

    @staticmethod
    def _log(version_id: int | None) -> None:
        if version_id is None:
            logger.info("Feed unchanged")
        else:
            logger.info("Timetable version %d active", version_id)


@contextmanager
def timed(label: str) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        logger.info("%s: %.1fs", label, time.perf_counter() - start)
