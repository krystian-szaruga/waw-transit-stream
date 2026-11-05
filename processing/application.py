from __future__ import annotations

import logging
import threading

from py4j.protocol import Py4JJavaError
from pyspark import Broadcast
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.streaming import StreamingQuery, StreamingQueryException

from config import ProcessingConfig
from database import create_timetable_reader
from processing.assignment import AssignmentPipeline
from processing.console_stats import start_console_query
from processing.lookup import LookupLoader
from processing.model import Lookup
from processing.session import SparkSessionContext
from processing.source import LiveReader

logger = logging.getLogger("warsaw_transit_stream_processing")


class Application:
    def __init__(self, config: ProcessingConfig) -> None:
        self._config = config
        self._stop = threading.Event()

    def stop(self) -> None:
        logger.info("Received termination request. Initiating graceful shutdown.")
        self._stop.set()

    def run(self) -> None:
        lookup = LookupLoader(create_timetable_reader()).load()
        with SparkSessionContext() as spark:
            if spark is None:
                logger.critical("Failed to acquire an active SparkSession. Exiting.")
                return
            broadcast = spark.sparkContext.broadcast(lookup)
            matched = self._matched(spark, broadcast)
            console: StreamingQuery = start_console_query(matched)
            self._await(console)
            broadcast.destroy()

    def _matched(self, spark: SparkSession, lookup_bc: Broadcast[Lookup]) -> DataFrame:
        live: DataFrame = LiveReader(spark, self._config.kafka).read()
        return AssignmentPipeline(lookup_bc).build(live)

    def _await(self, console: StreamingQuery) -> None:
        try:
            while console.isActive and not self._stop.is_set():
                self._stop.wait(timeout=2.0)
        except KeyboardInterrupt:
            self._stop.set()

        self._drain(console)

        if console.isActive:
            console.stop()
        console.awaitTermination()

    @staticmethod
    def _drain(console: StreamingQuery) -> None:
        if not console.isActive:
            return
        try:
            console.processAllAvailable()
        except (StreamingQueryException, Py4JJavaError):
            logger.exception("Failed to drain streaming query before stopping")
