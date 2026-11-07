import logging
import sys
import warnings

from waw_transit.database import create_timetable_reader, create_version_reader
from waw_transit.database.redis import open_live_state_repository
from waw_transit_pipeline.adapters.kafka import stream_options, topic_to_vehicle_type
from waw_transit_pipeline.adapters.spark import open_stream, parse_records
from waw_transit_pipeline.adapters.spark import session
from waw_transit_pipeline.core.config import KafkaConfigLoader
from waw_transit_pipeline.processing import ProcessingService
from waw_transit_pipeline.processing.config import ProcessingConfigLoader


def run_processing() -> None:
    _setup_logging()
    config = ProcessingConfigLoader().load()
    kafka_config = KafkaConfigLoader().load()
    live_reader = parse_records(
        open_stream("kafka", stream_options(kafka_config)),
        value_column="value",
        topic_column="topic",
        topic_to_type=topic_to_vehicle_type(kafka_config),
    )
    with open_live_state_repository(config.timezone) as repository:
        service = ProcessingService(
            config,
            repository,
            create_timetable_reader(),
            create_version_reader(),
            live_reader,
        )
        with session.open_session(timezone=config.timezone) as spark:
            service.run(spark)


def _setup_logging() -> None:
    warnings.filterwarnings(
        "ignore",
        message="The behavior of DataFrame concatenation with empty or all-NA entries is deprecated",
        category=FutureWarning,
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


if __name__ == "__main__":
    run_processing()
