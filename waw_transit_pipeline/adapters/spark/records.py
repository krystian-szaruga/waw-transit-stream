from __future__ import annotations

from collections.abc import Mapping
from typing import override

import pyspark.sql.functions as F
from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql.types import DataType, DoubleType, StringType, StructField, StructType

from waw_transit_pipeline.core.models import WarsawLiveCol
from waw_transit_pipeline.core.ports import StreamReader

_PAYLOAD_TYPES: dict[WarsawLiveCol, DataType] = {
    WarsawLiveCol.LINE: StringType(),
    WarsawLiveCol.BRIGADE: StringType(),
    WarsawLiveCol.VEHICLE_NUMBER: StringType(),
    WarsawLiveCol.LON: DoubleType(),
    WarsawLiveCol.LAT: DoubleType(),
    WarsawLiveCol.TIME: StringType(),
}


class _ParsedRecords(StreamReader[SparkSession, DataFrame]):
    def __init__(
        self,
        source: StreamReader[SparkSession, DataFrame],
        value_column: str,
        topic_column: str,
        topic_to_type: Mapping[str, int],
    ) -> None:
        self._source = source
        self._value_column = value_column
        self._topic_column = topic_column
        self._topic_to_type = topic_to_type
        self._payload_schema = StructType([
            StructField(col.value, dtype, True) for col, dtype in _PAYLOAD_TYPES.items()
        ])

    @override
    def read(self, session: SparkSession) -> DataFrame:
        raw = self._source.read(session)
        return (
            raw.select(self._vehicle_type_column(), self._payload_column())
            .select(WarsawLiveCol.VEHICLE_TYPE, "d.*")
        )

    def _vehicle_type_column(self) -> Column:
        mapping = F.create_map(*[F.lit(x) for kv in self._topic_to_type.items() for x in kv])
        return mapping[F.col(self._topic_column)].cast("int").alias(WarsawLiveCol.VEHICLE_TYPE)

    def _payload_column(self) -> Column:
        return F.from_json(F.col(self._value_column).cast("string"), self._payload_schema).alias("d")


def parse_records(
    source: StreamReader[SparkSession, DataFrame],
    value_column: str,
    topic_column: str,
    topic_to_type: Mapping[str, int],
) -> StreamReader[SparkSession, DataFrame]:
    return _ParsedRecords(source, value_column, topic_column, topic_to_type)
