import logging
import signal
import sys
import warnings

from processing.pipeline_service import PipelineService
from processing.config import ProcessingConfig, ProcessingConfigLoader


def _main() -> None:
    _setup_logging()
    logger = logging.getLogger("warsaw_transit_stream_processing")
    logger.info("Loading configuration...")
    config: ProcessingConfig = ProcessingConfigLoader().load()
    service = PipelineService(config)
    signal.signal(signal.SIGINT, lambda *_: service.stop())
    signal.signal(signal.SIGTERM, lambda *_: service.stop())
    service.run()


def _setup_logging() -> None:
    warnings.filterwarnings(
        "ignore",
        message="The behavior of DataFrame concatenation with empty or all-NA entries is deprecated",
        category=FutureWarning,
    )
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


if __name__ == '__main__':
    _main()
