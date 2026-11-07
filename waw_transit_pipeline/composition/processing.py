import logging
import sys
import warnings

from waw_transit.database import create_timetable_reader, create_version_reader
from waw_transit.database.redis import open_live_state_repository
from waw_transit_pipeline.processing import ProcessingService
from waw_transit_pipeline.processing.config import ProcessingConfigLoader


def run_processing() -> None:
    _setup_logging()
    config = ProcessingConfigLoader().load()
    with open_live_state_repository(config.timezone) as repository:
        ProcessingService(
            config,
            repository,
            create_timetable_reader(),
            create_version_reader(),
        ).run()


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
