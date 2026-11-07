import functools
import logging
import time

import functools
import logging
import time

logger = logging.getLogger("ProducerMonitoring")

def log_kafka_streaming(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        client_name = self._client.__class__.__name__
        topic = self._topic
        logger.info(f"[{client_name}] Launching ingestion cycle for topic '{topic}'...")
        start_time = time.time()
        try:
            record_count = func(self, *args, **kwargs)
            duration = time.time() - start_time
            if record_count > 0:
                logger.info(
                    f"[{client_name}] Successfully dispatched {record_count} messages to Kafka in {duration:.2f}s.")
            else:
                logger.warning(f"[{client_name}] Zero records retrieved during this execution cycle!")
            return record_count
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[{client_name}] Pipeline crashed after {duration:.2f}s. Reason: {e}", exc_info=True)
            raise e
    return wrapper
