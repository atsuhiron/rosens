import threading
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import cast

import polars as pl

from rosens.config import get_config
from rosens.models.sensor_data import SensorData, SensorRecord
from rosens.util import TZ


class Storage:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._lock = threading.Lock()

    def _file_path_for(self, recieved_at: datetime) -> Path:
        return self._data_dir / f"{recieved_at:%Y-%m-%d}.parquet"

    def save_sensor_data(self, sensor_data: SensorData, recieved_at: datetime) -> None:
        row = pl.DataFrame(
            {
                "sensor_id": [sensor_data.sensor_id],
                "temperature": [sensor_data.temperature],
                "humidity": [sensor_data.humidity],
                "pressure": [sensor_data.pressure],
                "uptime_s": [sensor_data.uptime_s],
                "recieved_at": [recieved_at],
            },
            # Readings are stored as FLOAT and uptime as INT32 in parquet; polars would
            # otherwise default python floats/ints to Float64/Int64.
            schema_overrides={
                "temperature": pl.Float32,
                "humidity": pl.Float32,
                "pressure": pl.Float32,
                "uptime_s": pl.Int32,
            },
        )

        path = self._file_path_for(recieved_at)

        # Parquet has no native append, so the daily file is read, combined with the
        # new row, and rewritten. The instance-wide lock keeps concurrent requests
        # (FastAPI runs sync endpoints in a threadpool) from clobbering each other.
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                existing = pl.read_parquet(path)
                combined = pl.concat([existing, row])
            else:
                combined = row
            combined.write_parquet(path)

    def load_sensor_data(self, start: datetime, end: datetime) -> list[SensorRecord]:
        # Daily files are bucketed by JST date, so the range of candidate files is
        # derived from the JST dates of the query bounds.
        first_day = start.astimezone(TZ).date()
        last_day = end.astimezone(TZ).date()

        # Reads take the lock too: save_sensor_data rewrites the whole file, and a
        # concurrent read could otherwise see a partially written parquet file.
        with self._lock:
            frames = []
            day = first_day
            while day <= last_day:
                path = self._data_dir / f"{day:%Y-%m-%d}.parquet"
                if path.exists():
                    frames.append(pl.read_parquet(path))
                day += timedelta(days=1)

        if not frames:
            return []
        df = pl.concat(frames).filter(pl.col("recieved_at").is_between(start, end)).sort("recieved_at")
        # to_dicts() is untyped (list[dict[str, Any]]); the parquet schema guarantees these keys.
        rows = cast("list[SensorRecord]", df.to_dicts())
        # Parquet normalizes tz-aware datetimes to UTC; convert back to JST so API
        # responses are consistently in the system timezone.
        for row in rows:
            row["recieved_at"] = row["recieved_at"].astimezone(TZ)
        return rows


# Cached so the whole app shares one instance — and therefore one lock.
@lru_cache(maxsize=1)
def get_storage() -> Storage:
    return Storage(data_dir=get_config().data_dir)
