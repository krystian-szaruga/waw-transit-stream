from __future__ import annotations

from collections.abc import Mapping
from typing import override

from pyspark.sql import DataFrame, SparkSession

from waw_transit_pipeline.core.ports import StreamReader


class _SparkStream(StreamReader[SparkSession, DataFrame]):
    def __init__(self, format: str, options: Mapping[str, str]) -> None:
        self._format = format
        self._options = options

    @override
    def read(self, session: SparkSession) -> DataFrame:
        stream = session.readStream.format(self._format)
        for key, value in self._options.items():
            stream = stream.option(key, value)
        return stream.load()


def open_stream(format: str, options: Mapping[str, str]) -> StreamReader[SparkSession, DataFrame]:
    return _SparkStream(format, options)
