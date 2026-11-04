from __future__ import annotations

from pyspark.sql.types import (
    BinaryType,
    DataType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from processing.model import TripMatchCol


class Schema:
    _TYPES: dict[TripMatchCol, DataType] = {
        TripMatchCol.TRIP_ID: StringType(),
        TripMatchCol.DIST_M: DoubleType(),
        TripMatchCol.DELAY_SEC: DoubleType(),
        TripMatchCol.COST: DoubleType(),
        TripMatchCol.MATCH_STATUS: StringType(),
        TripMatchCol.VEHICLE_TYPE: IntegerType(),
        TripMatchCol.VEHICLE_NUMBER: StringType(),
        TripMatchCol.BRIGADE: StringType(),
        TripMatchCol.LINE: StringType(),
        TripMatchCol.API_TS: TimestampType(),
    }

    @staticmethod
    def output() -> StructType:
        schema = StructType()
        for column in TripMatchCol:
            schema.add(column.value, Schema._TYPES[column])
        return schema

    @staticmethod
    def state() -> StructType:
        return StructType([
            StructField("vehicles", BinaryType(), True),
            StructField("owners", BinaryType(), True),
        ])
