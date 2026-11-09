import logging
import signal
import threading
from typing import List

from waw_transit_pipeline.core.ports import LiveVehicleClient, Publisher
from waw_transit_pipeline.ingest.config import IngestAppConfig
from waw_transit_pipeline.ingest.pipeline import WarsawTransitPipeline
from waw_transit_pipeline.ingest.publisher import IngestTransitPublisher

logger = logging.getLogger("warsaw_transit_stream_ingest")


class IngestService:
    def __init__(
        self,
        config: IngestAppConfig,
        buses: Publisher,
        trams: Publisher,
        buses_client: LiveVehicleClient,
        trams_client: LiveVehicleClient,
    ) -> None:
        self._config = config
        self._buses = buses
        self._trams = trams
        self._buses_client = buses_client
        self._trams_client = trams_client
        self._stop_event = threading.Event()

    def start(self) -> None:
        self._register_system_signals()
        logger.info("Loading centralized ingest application configuration...")
        publishers = self._build_transit_publishers()
        pipeline = WarsawTransitPipeline(
            config=self._config,
            publishers=publishers,
            publisher=self._buses,
            stop_event=self._stop_event,
        )
        logger.info("Warsaw Transit Ingestion Pipeline active. Orchestrating loops...")
        pipeline.run()
        logger.info("Ingest system shutdown complete. System exit: 0.")

    def _signal_handler(self, signum: int, frame) -> None:
        logger.info("Received system signal %d. Triggering graceful ingest shutdown.", signum)
        self._stop_event.set()
        logger.info("Flushing remaining message payloads...")
        self._buses.flush(5.0)

    def _register_system_signals(self) -> None:
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _build_transit_publishers(self) -> List[IngestTransitPublisher]:
        bus_publisher = IngestTransitPublisher(
            client=self._buses_client,
            publisher=self._buses,
        )
        tram_publisher = IngestTransitPublisher(
            client=self._trams_client,
            publisher=self._trams,
        )
        return [bus_publisher, tram_publisher]
