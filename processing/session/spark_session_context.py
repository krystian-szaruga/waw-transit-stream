import logging
from types import TracebackType
from typing import Optional, Type

from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)


class SparkSessionContext:
    """Context manager that owns a SparkSession and refuses to start
    if one is already active. Holds no global or class-level state."""

    def __init__(
        self,
        app_name: str = "WarsawTransitRealTimeStream",
        packages: str = (
            "org.apache.spark:spark-sql-kafka-0-10_2.13:4.2.0,"
            "org.postgresql:postgresql:42.7.1"
        ),
        shuffle_partitions: int = 2,
        log_level: str = "WARN",
    ) -> None:
        self._app_name = app_name
        self._packages = packages
        self._shuffle_partitions = shuffle_partitions
        self._log_level = log_level
        self._session: Optional[SparkSession] = None

    def __enter__(self) -> SparkSession | None:
        if SparkSession.getActiveSession() is not None:
            raise RuntimeError("A SparkSession is already active in this process.")
        try:
            logger.info("Starting SparkSession '%s'", self._app_name)
            self._session = (
                SparkSession.builder.appName(self._app_name)
                .config("spark.jars.packages", self._packages)
                .config("spark.sql.session.timeZone", "Europe/Warsaw")
                .config("spark.sql.shuffle.partitions", str(self._shuffle_partitions))
                .config("spark.sql.streaming.schemaInference", "true")
                .getOrCreate()
            )
            if self._session is not None:
                self._session.sparkContext.setLogLevel(self._log_level)
            return self._session
        except BaseException:
            self._stop()  # __exit__ won't run if __enter__ raises
            raise

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self._stop()

    def _stop(self) -> None:
        if self._session is not None:
            logger.info("Stopping SparkSession")
            self._session.stop()
            self._session = None
