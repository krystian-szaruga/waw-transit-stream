import logging
import signal
import threading
from typing import List, Optional

from confluent_kafka import Producer

from waw_transit_pipeline.ingest.config import IngestAppConfig
from waw_transit_pipeline.ingest.pipeline import WarsawTransitPipeline
from waw_transit_pipeline.ingest.producer import IngestTransitDataProducer
from waw_transit_pipeline.ingest.request import WarsawBusesClient, WarsawTramsClient

logger = logging.getLogger("warsaw_transit_stream_ingest")


class IngestService:
    def __init__(self, config: IngestAppConfig) -> None:
        self._config = config
        self._stop_event = threading.Event()
        self._shared_producer: Optional[Producer] = None

    def start(self) -> None:
        self._register_system_signals()
        logger.info("Loading centralized ingest application configuration...")
        self._shared_producer = self._initialize_kafka_producer()
        if self._shared_producer is None:
            raise RuntimeError("Fatal error: Kafka producer failed to initialize.")
        producers = self._build_transit_producers()
        pipeline = WarsawTransitPipeline(
            config=self._config,
            producers=producers,
            producer_client=self._shared_producer,
            stop_event=self._stop_event,
        )
        logger.info("Warsaw Transit Ingestion Pipeline active. Orchestrating loops...")
        pipeline.run()
        logger.info("Ingest system shutdown complete. System exit: 0.")

    def _signal_handler(self, signum: int, frame) -> None:
        logger.info("Received system signal %d. Triggering graceful ingest shutdown.", signum)
        self._stop_event.set()
        if self._shared_producer is not None:
            logger.info("Flushing remaining message payloads to Kafka broker...")
            self._shared_producer.flush(timeout=5.0)

    def _register_system_signals(self) -> None:
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _initialize_kafka_producer(self) -> Producer:
        kafka_config = {
            "bootstrap.servers": self._config.kafka.bootstrap_servers,
            "client.id": self._config.kafka.client_id,
            "acks": "all",
            "retries": 5,
            "linger.ms": 20,
        }
        return Producer(kafka_config)

    def _build_transit_producers(self) -> List[IngestTransitDataProducer]:
        if self._shared_producer is None:
            return []
        bus_producer = IngestTransitDataProducer(
            client=WarsawBusesClient(self._config.api.warsaw_api_token),
            producer=self._shared_producer,
            topic=self._config.kafka.topic_buses,
        )
        tram_producer = IngestTransitDataProducer(
            client=WarsawTramsClient(self._config.api.warsaw_api_token),
            producer=self._shared_producer,
            topic=self._config.kafka.topic_trams,
        )
        return [bus_producer, tram_producer]
