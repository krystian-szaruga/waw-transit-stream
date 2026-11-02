import logging
import signal
import sys
import threading
from typing import List, Optional

from confluent_kafka import Producer

from config import IngestConfigLoader, IngestAppConfig
from pipeline import WarsawTransitPipeline
from producer import IngestTransitDataProducer
from request import WarsawBusesClient, WarsawTramsClient

logger = logging.getLogger("warsaw_transit_stream_ingest")


class _IngestAppOrchestrator:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._shared_producer: Optional[Producer] = None

    def start(self) -> None:
        self._setup_logging()
        self._register_system_signals()
        logger.info("Loading centralized ingest application configuration...")
        config_obj = IngestConfigLoader().load()
        self._shared_producer = self._initialize_kafka_producer(config_obj)
        if self._shared_producer is None:
            raise RuntimeError("Fatal error: Kafka producer failed to initialize.")
        producers = self._build_transit_producers(config_obj, self._shared_producer)
        pipeline = WarsawTransitPipeline(
            config=config_obj,
            producers=producers,
            producer_client=self._shared_producer,
            stop_event=self._stop_event
        )
        logger.info("Warsaw Transit Ingestion Pipeline active. Orchestrating loops...")
        pipeline.run()
        logger.info("Ingest system shutdown complete. System exit: 0.")

    @staticmethod
    def _setup_logging() -> None:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )

    def _signal_handler(self, signum: int, frame) -> None:
        logger.info("Received system signal %d. Triggering graceful ingest shutdown.", signum)
        self._stop_event.set()

        if self._shared_producer is not None:
            logger.info("Flushing remaining message payloads to Kafka broker...")
            self._shared_producer.flush(timeout=5.0)

    def _register_system_signals(self) -> None:
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    @staticmethod
    def _initialize_kafka_producer(config: IngestAppConfig) -> Producer:
        kafka_config = {
            'bootstrap.servers': config.kafka.bootstrap_servers,
            'client.id': config.kafka.client_id,
            'acks': 'all',
            'retries': 5,
            'linger.ms': 20
        }
        return Producer(kafka_config)

    @staticmethod
    def _build_transit_producers(config: IngestAppConfig, producer: Producer) -> List[IngestTransitDataProducer]:
        bus_producer = IngestTransitDataProducer(
            client=WarsawBusesClient(config.api.warsaw_api_token),
            producer=producer,
            topic=config.kafka.topic_buses
        )
        tram_producer = IngestTransitDataProducer(
            client=WarsawTramsClient(config.api.warsaw_api_token),
            producer=producer,
            topic=config.kafka.topic_trams
        )
        return [bus_producer, tram_producer]


def _main() -> None:
    orchestrator = _IngestAppOrchestrator()
    orchestrator.start()


if __name__ == '__main__':
    _main()
