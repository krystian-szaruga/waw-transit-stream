import logging
from threading import Event
from typing import List

from confluent_kafka import Producer

from ingest.config import IngestAppConfig
from pipeline.log_pipeline_cycle import log_pipeline_cycle
from producer import IngestTransitDataProducer

logger = logging.getLogger(__name__)


class WarsawTransitPipeline:
    def __init__(
            self,
            config: IngestAppConfig,
            producers: List[IngestTransitDataProducer],
            producer_client: Producer,
            stop_event: Event
    ) -> None:
        self._config = config
        self._producers = producers
        self._producer_client = producer_client
        self._stop_event = stop_event

    def run(self) -> None:
        interval = getattr(self._config.api, "request_interval_seconds", 15)
        while not self._stop_event.is_set():
            self._execute_cycle()
            self._stop_event.wait(timeout=float(interval))

    @log_pipeline_cycle
    def _execute_cycle(self) -> None:
        for producer in self._producers:
            producer.execute()
        self._producer_client.poll(0)
