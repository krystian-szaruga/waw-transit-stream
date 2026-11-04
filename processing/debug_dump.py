import pickle
import re
from pathlib import Path

import pandas as pd
from pyspark.sql import DataFrame
from pyspark.sql.streaming import StreamingQuery

from processing.model import Lookup, MatchStatus, TripMatchCol

DUMP_ENABLED = True
DUMP_DIR = Path(__file__).parent / "dumps"
DUMP_CHECKPOINT = "/tmp/ckpt_dump"
MIN_DELAY_SEC = 600.0
TOP_N_PER_BATCH = 5

_VT = TripMatchCol.VEHICLE_TYPE.value
_VN = TripMatchCol.VEHICLE_NUMBER.value
_TRIP = TripMatchCol.TRIP_ID.value
_LINE = TripMatchCol.LINE.value
_DELAY = TripMatchCol.DELAY_SEC.value
_STATUS = TripMatchCol.MATCH_STATUS.value


def save_lookup(lookup: Lookup, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(lookup, f)


def load_lookup(path: Path) -> Lookup:
    with open(path, "rb") as f:
        return pickle.load(f)


class _WorstDelayDumper:
    def __init__(self, out_dir: Path) -> None:
        self._out_dir = out_dir
        self._saved: set[tuple[int, str, str]] = set()

    def __call__(self, batch_df: DataFrame, batch_id: int) -> None:
        pdf = batch_df.toPandas()
        if pdf.empty:
            return

        valid = pdf[
            pdf[_DELAY].notna()
            & (pdf[_STATUS] != MatchStatus.LAYOVER.value)
            & (pdf[_DELAY] >= MIN_DELAY_SEC)
        ].sort_values(_DELAY, ascending=False)
        if valid.empty:
            return

        saved = 0
        for _, row in valid.iterrows():
            if saved >= TOP_N_PER_BATCH:
                break
            vehicle_type = int(row[_VT])
            vehicle_number = str(row[_VN])
            trip_id = str(row[_TRIP])
            key = (vehicle_type, vehicle_number, trip_id)
            if key in self._saved:
                continue
            self._saved.add(key)
            saved += 1

            delay = float(row[_DELAY])
            line = re.sub(r"[^\w.-]", "_", str(row[_LINE]))
            stem = f"worst_line{line}_{vehicle_type}_{vehicle_number}_b{batch_id}_delay{int(delay)}"
            self._out_dir.mkdir(parents=True, exist_ok=True)
            valid[
                (valid[_VT] == vehicle_type) & (valid[_VN] == vehicle_number)
            ].to_parquet(self._out_dir / f"{stem}.parquet")


def start_dump(matched: DataFrame, lookup: Lookup) -> StreamingQuery | None:
    if not DUMP_ENABLED:
        return None
    save_lookup(lookup, DUMP_DIR / "lookup.pkl")
    return (
        matched.writeStream
        .foreachBatch(_WorstDelayDumper(DUMP_DIR))
        .option("checkpointLocation", DUMP_CHECKPOINT)
        .start()
    )
