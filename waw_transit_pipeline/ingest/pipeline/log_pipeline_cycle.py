import functools
import logging
import time

logger = logging.getLogger("PipelineMonitoring")


def log_pipeline_cycle(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> float:
        logger.info("Starting global pipeline execution cycle...")
        start_time = time.time()
        try:
            func(self, *args, **kwargs)
            duration = time.time() - start_time
            sleep_time = max(0.1, self._config.fetch_interval_seconds - duration)
            logger.info(f"Global cycle completed in {duration:.2f}s. Streaming batches flushed. Sleeping for {sleep_time:.2f}s...")
            return sleep_time
        except Exception as e:
            logger.error(f"Global pipeline cycle crashed! Reason: {e}", exc_info=True)
            raise e
    return wrapper
