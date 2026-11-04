import logging
import signal
import sys

from application import Application
from config import ProcessingConfig, ProcessingConfigLoader


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def _main() -> None:
    _setup_logging()
    logger = logging.getLogger("warsaw_transit_stream_processing")
    logger.info("Loading configuration...")
    config: ProcessingConfig = ProcessingConfigLoader().load()

    application = Application(config)
    signal.signal(signal.SIGINT, lambda *_: application.stop())
    signal.signal(signal.SIGTERM, lambda *_: application.stop())
    application.run()


if __name__ == '__main__':
    _main()
