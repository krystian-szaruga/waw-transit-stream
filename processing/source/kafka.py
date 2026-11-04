from pyspark.sql import Column, DataFrame, SparkSession, functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType, DataType

from processing.config import KafkaConfig
from processing.model import WarsawLiveCol


class LiveReader:
    _PAYLOAD_TYPES: dict[WarsawLiveCol, DataType] = {
        WarsawLiveCol.LINE: StringType(),
        WarsawLiveCol.BRIGADE: StringType(),
        WarsawLiveCol.VEHICLE_NUMBER: StringType(),
        WarsawLiveCol.LON: DoubleType(),
        WarsawLiveCol.LAT: DoubleType(),
        WarsawLiveCol.TIME: StringType(),
    }
    def __init__(self, spark: SparkSession, config: KafkaConfig) -> None:
        self._spark = spark
        self._config = config
        self._topic_to_type = {topic: int(vtype) for vtype, topic in config.topics.items()}
        self._payload_schema = StructType([
            StructField(col.value, dtype, True) for col, dtype in self._PAYLOAD_TYPES.items()
        ])

    def read(self) -> DataFrame:
        return self._parse(self._load_raw())

    def _load_raw(self) -> DataFrame:
        return (
            self._spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", self._config.bootstrap_servers)
            .option("subscribe", ",".join(self._topic_to_type))
            .option("startingOffsets", self._config.starting_offsets)
            .option("failOnDataLoss", "false")
            .load()
        )

    def _parse(self, raw: DataFrame) -> DataFrame:
        return (
            raw.select(self._vehicle_type_column(), self._payload_column())
            .select(WarsawLiveCol.VEHICLE_TYPE, "d.*")
        )

    def _vehicle_type_column(self) -> Column:
        mapping = F.create_map(*[F.lit(x) for kv in self._topic_to_type.items() for x in kv])
        return mapping[F.col("topic")].cast("int").alias(WarsawLiveCol.VEHICLE_TYPE)

    def _payload_column(self) -> Column:
        return F.from_json(F.col("value").cast("string"), self._payload_schema).alias("d")
