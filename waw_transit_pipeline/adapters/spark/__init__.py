from .records import parse_records
from .stream import open_stream

KAFKA_SPARK_PACKAGE = "org.apache.spark:spark-sql-kafka-0-10_2.13:4.3.0"
POSTGRES_SPARK_PACKAGE = "org.postgresql:postgresql:42.7.1"

required_packages = (KAFKA_SPARK_PACKAGE, POSTGRES_SPARK_PACKAGE)

__all__ = [
    "KAFKA_SPARK_PACKAGE",
    "POSTGRES_SPARK_PACKAGE",
    "open_stream",
    "parse_records",
    "required_packages",
]
