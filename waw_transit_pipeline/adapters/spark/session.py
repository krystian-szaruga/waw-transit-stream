from __future__ import annotations
import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import override

from pyspark.sql import SparkSession

from waw_transit.config import ConfigLoader
from waw_transit_pipeline.adapters.spark import required_packages

logger = logging.getLogger(__name__)


@contextmanager
def open_session(
        timezone: str = "Europe/Warsaw",
        app_name: str = "WarsawTransitRealTimeStream",
        shuffle_partitions: int = 2,
        log_level: str = "WARN",
) -> Iterator[SparkSession]:
    _SparkEnvConfigLoader().load()
    if SparkSession.getActiveSession() is not None:
        raise RuntimeError("A SparkSession is already active in this process.")
    logger.info("Starting SparkSession '%s'", app_name)
    session = (
        SparkSession.builder.appName(app_name)
        .config("spark.jars.packages", ",".join(required_packages))
        .config("spark.sql.session.timeZone", timezone)
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
        .config("spark.sql.streaming.schemaInference", "true")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel(log_level)
    try:
        yield session
    finally:
        logger.info("Stopping SparkSession")
        session.stop()



@dataclass(frozen=True)
class _SparkEnvConfig:
    java_home: str
    local_ip: str
    local_hostname: str


class _SparkEnvConfigLoader(ConfigLoader[_SparkEnvConfig]):
    @override
    def _read(self) -> _SparkEnvConfig:
        config = _SparkEnvConfig(
            java_home=self._env_reader.get("JAVA_HOME", ""),
            local_ip=self._env_reader.get("LOCAL_IP", ""),
            local_hostname=self._env_reader.get("LOCAL_HOSTNAME", ""),
        )
        self._apply_environment(config)
        return config

    @staticmethod
    def _apply_environment(config: _SparkEnvConfig) -> None:
        if config.java_home:
            os.environ.setdefault("JAVA_HOME", config.java_home)
        if config.local_ip:
            os.environ.setdefault("SPARK_LOCAL_IP", config.local_ip)
        if config.local_hostname:
            os.environ.setdefault("SPARK_LOCAL_HOSTNAME", config.local_hostname)

