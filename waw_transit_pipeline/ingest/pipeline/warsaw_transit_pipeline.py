import logging
from threading import Event
from typing import List

from waw_transit_pipeline.core.ports import Publisher
from waw_transit_pipeline.ingest.config import IngestAppConfig
from waw_transit_pipeline.ingest.pipeline.log_pipeline_cycle import log_pipeline_cycle
from waw_transit_pipeline.ingest.publisher import IngestTransitPublisher

logger = logging.getLogger(__name__)


class WarsawTransitPipeline:
    def __init__(
            self,
            config: IngestAppConfig,
            publishers: List[IngestTransitPublisher],
            publisher: Publisher,
            stop_event: Event
    ) -> None:
        self._config = config
        self._publishers = publishers
        self._publisher = publisher
        self._stop_event = stop_event

    def run(self) -> None:
        interval = self._config.fetch_interval_seconds
        while not self._stop_event.is_set():
            self._execute_cycle()
            self._stop_event.wait(timeout=float(interval))

    @log_pipeline_cycle
    def _execute_cycle(self) -> None:
        for publisher in self._publishers:
            publisher.execute()
        self._publisher.poll()
