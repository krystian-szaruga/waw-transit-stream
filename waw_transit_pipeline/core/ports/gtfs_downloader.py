from abc import ABC, abstractmethod

from waw_transit_pipeline.core.models import Gtfs


class GtfsDownloader(ABC):

    @abstractmethod
    def download(
        self,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> Gtfs | None:
        pass
