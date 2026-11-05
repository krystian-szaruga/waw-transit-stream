from __future__ import annotations

import logging
import threading
import time

import psycopg2
from py4j.protocol import Py4JJavaError
from pyspark import Broadcast
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.streaming import StreamingQuery, StreamingQueryException

from console_stats import start_console_query
from database import create_timetable_reader, create_version_reader
from processing.assignment import AssignmentPipeline
from processing.config import ProcessingConfig
from processing.lookup import LookupLoader
from processing.model import LookupSnapshot
from processing.session import SparkSessionContext
from processing.source import LiveReader

logger = logging.getLogger("warsaw_transit_stream_processing")


class PipelineService:
    _VERSION_POLL_SEC = 10.0
    _IDLE_POLL_SEC = 0.2
    _IDLE_TIMEOUT_SEC = 60.0

    def __init__(self, config: ProcessingConfig) -> None:
        self._config = config
        self._stop = threading.Event()

    def stop(self) -> None:
        logger.info("Received termination request. Initiating graceful shutdown.")
        self._stop.set()

    def run(self) -> None:
        logger.info("Loading timetable lookup...")
        snapshot = LookupLoader(create_timetable_reader()).load()
        versions = create_version_reader()
        logger.info("Loaded timetable version %d", snapshot.version_id)
        with SparkSessionContext() as spark:
            if spark is None:
                logger.critical("Failed to acquire an active SparkSession. Exiting.")
                return
            while not self._stop.is_set():
                broadcast = spark.sparkContext.broadcast(snapshot)
                console: StreamingQuery = start_console_query(
                    self._matched(spark, broadcast)
                    .writeStream
                    .option("checkpointLocation", self._config.checkpoint_location)
                )
                changed = self._await(console, versions, snapshot.version_id)
                self._stop_when_idle(console)
                broadcast.destroy()
                if changed and not self._stop.is_set():
                    snapshot = self._reload(snapshot)
                    continue
                return

    def _reload(self, current: LookupSnapshot) -> LookupSnapshot:
        while not self._stop.is_set():
            logger.info("Loading timetable lookup...")
            try:
                snapshot = LookupLoader(create_timetable_reader()).load()
            except (psycopg2.Error, RuntimeError):
                logger.exception(
                    "Failed to reload the lookup; keeping version %d", current.version_id
                )
                self._stop.wait(timeout=self._VERSION_POLL_SEC)
                continue
            logger.info("Reloaded lookup: version %d -> %d", current.version_id, snapshot.version_id)
            return snapshot
        return current

    def _matched(self, spark: SparkSession, lookup_bc: Broadcast[LookupSnapshot]) -> DataFrame:
        live: DataFrame = LiveReader(spark, self._config.kafka).read()
        return AssignmentPipeline(lookup_bc).build(live)

    def _await(self, console: StreamingQuery, versions, version_id: int) -> bool:
        try:
            while console.isActive and not self._stop.is_set():
                try:
                    active = versions.load()
                    logger.debug("Version poll: active %d, loaded %d", active, version_id)
                    if active != version_id:
                        logger.info("New version %d detected (loaded %d)", active, version_id)
                        return True
                except (psycopg2.Error, RuntimeError):
                    logger.exception(
                        "Failed to read the active GTFS version; keeping version %d", version_id
                    )
                self._stop.wait(timeout=self._VERSION_POLL_SEC)
        except KeyboardInterrupt:
            self._stop.set()
        return False

    @classmethod
    def _stop_when_idle(cls, console: StreamingQuery) -> None:
        deadline = time.monotonic() + cls._IDLE_TIMEOUT_SEC
        try:
            while (
                    console.isActive
                    and console.status.get("isTriggerActive")
                    and time.monotonic() < deadline
            ):
                time.sleep(cls._IDLE_POLL_SEC)
            if console.isActive:
                console.stop()
            console.awaitTermination()
        except (StreamingQueryException, Py4JJavaError):
            logger.exception("Streaming query terminated with an error while stopping")
