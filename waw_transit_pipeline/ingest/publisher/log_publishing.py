import functools
import logging
import time

logger = logging.getLogger("PublisherMonitoring")


def log_publishing(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        client_name = self._client.__class__.__name__
        logger.info(f"[{client_name}] Launching ingestion cycle...")
        start_time = time.time()
        try:
            record_count = func(self, *args, **kwargs)
            duration = time.time() - start_time
            if record_count > 0:
                logger.info(
                    f"[{client_name}] Successfully dispatched {record_count} messages in {duration:.2f}s.")
            else:
                logger.warning(f"[{client_name}] Zero records retrieved during this execution cycle!")
            return record_count
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[{client_name}] Pipeline crashed after {duration:.2f}s. Reason: {e}", exc_info=True)
            raise e
    return wrapper
