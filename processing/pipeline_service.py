from __future__ import annotations

import logging
import signal
import threading
import time
from dataclasses import dataclass

import psycopg2
from py4j.protocol import Py4JJavaError
from pyspark import Broadcast
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.streaming import StreamingQuery, StreamingQueryException

from database import create_timetable_reader, create_version_reader
from processing.assignment import AssignmentPipeline
from processing.config import ProcessingConfig, ProcessingConfigLoader
from processing.console_stats import console_stats
from processing.lookup import LookupLoader
from processing.model import LookupSnapshot
from processing.session import RedisSession, SparkSessionContext
from processing.sink import RedisSink
from processing.source import LiveReader

logger = logging.getLogger("warsaw_transit_stream_processing")


class PipelineService:
    _VERSION_POLL_SEC = 10.0
    _IDLE_POLL_SEC = 0.2
    _IDLE_TIMEOUT_SEC = 60.0

    def __init__(self) -> None:
        self._config: ProcessingConfig = ProcessingConfigLoader().load()
        self._stop = threading.Event()

    def stop(self) -> None:
        logger.info("Received termination request. Initiating graceful shutdown.")
        self._stop.set()

    def _register_system_signals(self) -> None:
        signal.signal(signal.SIGINT, lambda *_: self.stop())
        signal.signal(signal.SIGTERM, lambda *_: self.stop())

    def run(self) -> None:
        self._register_system_signals()
        logger.info("Loading timetable lookup...")
        snapshot = LookupLoader(create_timetable_reader()).load()
        versions = create_version_reader()
        logger.info("Loaded timetable version %d", snapshot.version_id)
        with RedisSession(self._config.redis) as session:
            with SparkSessionContext(self._config.timezone).open() as spark:
                gen = self._prepare(spark, session, snapshot)
                while not self._stop.is_set():
                    console = self._start(spark, gen)
                    changed = self._await(console, versions, gen.snapshot.version_id)
                    next_gen: _VersionContext | None = None
                    if changed and not self._stop.is_set():
                        next_gen = self._prepare_next(spark, session, gen.snapshot)
                    self._stop_when_idle(console)
                    gen.broadcast.destroy()
                    if next_gen is None:
                        return
                    if self._stop.is_set():
                        next_gen.broadcast.destroy()
                        return
                    gen = next_gen
                gen.broadcast.destroy()

    def _prepare(self, spark: SparkSession, session: RedisSession, snapshot: LookupSnapshot) -> _VersionContext:
        sink = RedisSink(session, snapshot.lookup, self._config.timezone)
        broadcast = spark.sparkContext.broadcast(snapshot)
        return _VersionContext(snapshot, sink, broadcast)

    def _prepare_next(self, spark: SparkSession, session: RedisSession, current: LookupSnapshot) -> _VersionContext | None:
        new_snapshot = self._reload(current)
        if new_snapshot is current: return None
        return self._prepare(spark, session, new_snapshot)

    def _start(self, spark: SparkSession, gen: _VersionContext) -> StreamingQuery:
        return (
            self._matched(spark, gen.broadcast)
            .writeStream
            .option("checkpointLocation", self._config.checkpoint_location)
            .trigger(processingTime="15 seconds")
            .foreachBatch(_BatchHandler(gen.sink))
            .start()
        )

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


@dataclass
class _VersionContext:
    snapshot: LookupSnapshot
    sink: RedisSink
    broadcast: Broadcast[LookupSnapshot]


class _BatchHandler:
    def __init__(self, sink: RedisSink) -> None:
        self._sink = sink

    def __call__(self, batch_df: DataFrame, batch_id: int) -> None:
        console_stats(batch_df, batch_id)
        self._sink.write(batch_df)