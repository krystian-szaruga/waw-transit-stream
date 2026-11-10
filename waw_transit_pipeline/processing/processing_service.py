from __future__ import annotations

import logging
import signal
import threading
import time
from dataclasses import dataclass

from py4j.protocol import Py4JJavaError
from pyspark import Broadcast
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.streaming import StreamingQuery, StreamingQueryException

from waw_transit.core import ReadRepository, RepositoryError, SaveRepository, VersionStore, ParameterlessReadRepository
from waw_transit_pipeline.core.ports import StreamReader, VersionWatcher
from waw_transit.core.models import LiveStateBatch
from waw_transit_pipeline.processing.assignment import AssignmentPipeline
from waw_transit_pipeline.processing.config import ProcessingConfig
from waw_transit_pipeline.processing.console_stats import console_stats
from waw_transit_pipeline.processing.lookup import LookupLoader
from waw_transit_pipeline.processing.model import LookupSnapshot
from waw_transit_pipeline.processing.sink.preparer import LiveStatePreparer

logger = logging.getLogger("warsaw_transit_stream_processing")


class ProcessingService:
    _VERSION_POLL_SEC = 10.0
    _VERSION_WAIT_SEC = 5.0
    _IDLE_POLL_SEC = 0.2
    _IDLE_TIMEOUT_SEC = 60.0

    def __init__(
        self,
        config: ProcessingConfig,
        sink: SaveRepository[LiveStateBatch, None],
        timetable_reader: ReadRepository,
        version_reader: ParameterlessReadRepository,
        watcher: VersionWatcher,
        version_store: VersionStore,
        stream_reader: StreamReader[SparkSession, DataFrame],
    ) -> None:
        self._config = config
        self._sink = sink
        self._timetable_reader = timetable_reader
        self._version_reader = version_reader
        self._watcher = watcher
        self._version_store = version_store
        self._stream_reader = stream_reader
        self._stop = threading.Event()

    def stop(self) -> None:
        logger.info("Received termination request. Initiating graceful shutdown.")
        self._stop.set()

    def _register_system_signals(self) -> None:
        signal.signal(signal.SIGINT, lambda *_: self.stop())
        signal.signal(signal.SIGTERM, lambda *_: self.stop())

    def run(self, spark: SparkSession) -> None:
        self._register_system_signals()
        logger.info("Loading timetable lookup...")
        snapshot = LookupLoader(self._timetable_reader).load()
        self._version_store.save(snapshot.version_id)
        logger.info("Loaded timetable version %d", snapshot.version_id)
        gen = self._prepare(spark, snapshot)
        while not self._stop.is_set():
            console = self._start(spark, gen)
            changed = self._await(console, gen.snapshot.version_id)
            next_gen: _VersionContext | None = None
            if changed and not self._stop.is_set():
                next_gen = self._prepare_next(spark, gen.snapshot)
                if next_gen is not None:
                    self._version_store.save(next_gen.snapshot.version_id)
                    self._watcher.commit()
            self._stop_when_idle(console)
            gen.broadcast.destroy()
            if next_gen is None:
                return
            if self._stop.is_set():
                next_gen.broadcast.destroy()
                return
            gen = next_gen
        if gen is not None:
            gen.broadcast.destroy()

    def _prepare_next(self, spark: SparkSession, current: LookupSnapshot) -> _VersionContext | None:
        new_snapshot = self._reload(current)
        if new_snapshot is current: return None
        return self._prepare(spark, new_snapshot)

    def _prepare(self, spark: SparkSession, snapshot: LookupSnapshot) -> _VersionContext:
        preparer = LiveStatePreparer(snapshot.lookup, self._config.timezone)
        broadcast = spark.sparkContext.broadcast(snapshot)
        return _VersionContext(snapshot, preparer, self._sink, broadcast)

    def _start(self, spark: SparkSession, gen: _VersionContext) -> StreamingQuery:
        return (
            self._matched(spark, gen.broadcast)
            .writeStream
            .option("checkpointLocation", self._config.checkpoint_location)
            .trigger(processingTime="15 seconds")
            .foreachBatch(_BatchHandler(gen.preparer, gen.sink, self._config.stats_enabled))
            .start()
        )

    def _reload(self, current: LookupSnapshot) -> LookupSnapshot:
        while not self._stop.is_set():
            logger.info("Loading timetable lookup...")
            try:
                snapshot = LookupLoader(self._timetable_reader).load()
            except RepositoryError as err:
                logger.error(
                    "Failed to reload the lookup; keeping version %d, %s",
                    current.version_id,
                    err,
                )
                self._stop.wait(timeout=self._VERSION_POLL_SEC)
                continue
            logger.info("Reloaded lookup: version %d -> %d", current.version_id, snapshot.version_id)
            return snapshot
        return current

    def _matched(self, spark: SparkSession, lookup_bc: Broadcast[LookupSnapshot]) -> DataFrame:
        live: DataFrame = self._stream_reader.read(spark)
        return AssignmentPipeline(lookup_bc).build(live)

    def _await(self, console: StreamingQuery, version_id: int) -> bool:
        try:
            while console.isActive and not self._stop.is_set():
                event = self._watcher.next_version(self._VERSION_WAIT_SEC)
                if event is None:
                    continue
                logger.info("Version event %d (loaded %d)", event, version_id)
                try:
                    active = self._version_reader.load()
                except RepositoryError as err:
                    logger.error(
                        "Failed to read the active GTFS version; keeping version %d, %s",
                        version_id,
                        err,
                    )
                    continue
                if active != version_id:
                    logger.info("New version %d detected (loaded %d)", active, version_id)
                    return True
                self._watcher.commit()
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
        except (StreamingQueryException, Py4JJavaError) as err:
            logger.error("Streaming query terminated with an error while stopping: %s", err)


@dataclass
class _VersionContext:
    snapshot: LookupSnapshot
    preparer: LiveStatePreparer
    sink: SaveRepository[LiveStateBatch, None]
    broadcast: Broadcast[LookupSnapshot]


class _BatchHandler:
    def __init__(
        self,
        preparer: LiveStatePreparer,
        sink: SaveRepository[LiveStateBatch, None],
        stats_enabled: bool,
    ) -> None:
        self._preparer = preparer
        self._sink = sink
        self._stats_enabled = stats_enabled

    def __call__(self, batch_df: DataFrame, batch_id: int) -> None:
        if self._stats_enabled:
            console_stats(batch_df, batch_id)
        self._sink.save(self._preparer.prepare(batch_df))