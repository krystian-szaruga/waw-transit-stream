import logging
from contextlib import contextmanager
from types import TracebackType
from typing import Optional, Type, Generator

from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)


class SparkSessionContext:
    def __init__(
            self,
            timezone: str = "Europe/Warsaw",
            app_name: str = "WarsawTransitRealTimeStream",
            packages: str = (
                    "org.apache.spark:spark-sql-kafka-0-10_2.13:4.3.0,"
                    "org.postgresql:postgresql:42.7.1"
            ),
            shuffle_partitions: int = 2,
            log_level: str = "WARN",
    ) -> None:
        self._timezone = timezone
        self._app_name = app_name
        self._packages = packages
        self._shuffle_partitions = shuffle_partitions
        self._log_level = log_level

    @contextmanager
    def open(self) -> Generator[SparkSession, None, None]:
        if SparkSession.getActiveSession() is not None:
            raise RuntimeError("A SparkSession is already active in this process.")
        logger.info("Starting SparkSession '%s'", self._app_name)
        session = (
            SparkSession.builder.appName(self._app_name)
            .config("spark.jars.packages", self._packages)
            .config("spark.sql.session.timeZone", self._timezone)
            .config("spark.sql.shuffle.partitions", str(self._shuffle_partitions))
            .config("spark.sql.streaming.schemaInference", "true")
            .getOrCreate()
        )
        session.sparkContext.setLogLevel(self._log_level)
        try:
            yield session
        finally:
            logger.info("Stopping SparkSession")
            session.stop()