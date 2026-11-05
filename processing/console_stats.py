from __future__ import annotations

import pyspark.sql.functions as F
from pyspark.sql import DataFrame, Window
from pyspark.sql.streaming import StreamingQuery, DataStreamWriter

from processing.model import MatchStatus, TripMatchCol


def start_console_query(writer: DataStreamWriter) -> StreamingQuery:
    return (
        writer
        .foreachBatch(_print_delay_stats)
        .trigger(processingTime="15 seconds")
        .start()
    )

def _print_delay_stats(batch_df: DataFrame, _: int) -> None:
    status = F.col(TripMatchCol.MATCH_STATUS.value)
    unmatched = batch_df.where(status == MatchStatus.UNMATCHED.value).count()
    batch_df = batch_df.where(status == MatchStatus.MATCHED.value)
    w = Window.partitionBy("vehicle_type", "vehicle_number").orderBy(F.col("api_timestamp").desc())
    active = (
        batch_df
        .withColumn("rn", F.row_number().over(w))
        .where("rn = 1")
        .drop("rn")
    )
    row = active.agg(
        F.count("*").alias("vehicles"),
        F.round(F.avg("delay_sec"), 1).alias("mean"),
        F.round(F.stddev("delay_sec"), 1).alias("stddev"),
        F.round(F.expr("percentile_approx(delay_sec, 0.5)"), 1).alias("median"),
        F.round(F.expr("percentile_approx(delay_sec, 0.9)"), 1).alias("p90"),
        F.round(F.expr("percentile_approx(delay_sec, 0.99)"), 1).alias("p99"),
        F.round(F.min("delay_sec"), 1).alias("min"),
        F.round(F.max("delay_sec"), 1).alias("max"),
        F.sum(F.when(F.col("delay_sec") > 600, 1).otherwise(0)).alias("over_10min"),
        F.sum(F.when(F.col("delay_sec") < -300, 1).otherwise(0)).alias("early_over_5min"),
        F.sum(F.when((F.col("delay_sec") >= -300) & (F.col("delay_sec") <= 600), 1).otherwise(0)).alias("within_window"),
    ).first()

    if row is None or row["vehicles"] == 0:
        print(f"delay stats: no matched vehicles in this batch (unmatched: {unmatched})")
        return

    n = row["vehicles"]
    seconds = lambda value: "n/a" if value is None else f"{value} s"
    rows = [
        ("vehicles", str(n)),
        ("mean", seconds(row["mean"])),
        ("median", seconds(row["median"])),
        ("stddev", seconds(row["stddev"])),
        ("min", seconds(row["min"])),
        ("max", seconds(row["max"])),
        ("p90", seconds(row["p90"])),
        ("p99", seconds(row["p99"])),
        ("late > 10 min", f"{row['over_10min']} ({100.0 * row['over_10min'] / n:.1f}%)"),
        ("early > 5 min", f"{row['early_over_5min']} ({100.0 * row['early_over_5min'] / n:.1f}%)"),
        ("within -5..+10 min", f"{row['within_window']} ({100.0 * row['within_window'] / n:.1f}%)"),
        ("unmatched (no trip)", str(unmatched)),
    ]
    label_width = max(len(label) for label, _ in rows)
    value_width = max(len(value) for _, value in rows)
    border = f"+{'-' * (label_width + 2)}+{'-' * (value_width + 2)}+"
    print(border)
    print(f"| {'metric':<{label_width}} | {'value':<{value_width}} |")
    print(border)
    for label, value in rows:
        print(f"| {label:<{label_width}} | {value:<{value_width}} |")
    print(border)
