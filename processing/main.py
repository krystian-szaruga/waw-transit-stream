import logging
import sys
import warnings

from processing import PipelineService


def _main() -> None:
    _setup_logging()
    PipelineService().run()


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
    _main()
