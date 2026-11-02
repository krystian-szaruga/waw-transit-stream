import logging
import time
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger(__name__)


@contextmanager
def timed(label: str) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        logger.info("%s: %.1fs", label, time.perf_counter() - start)
