import threading
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import cast

import polars as pl
from pydantic import BaseModel

from rosens.config import get_config
from rosens.datasets import Dataset
from rosens.util import TZ


class Storage:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._lock = threading.Lock()

    def _file_path(self, dataset: Dataset, day: date) -> Path:
        return self._data_dir / dataset.name / f"{day:%Y-%m-%d}.parquet"

    def save[RecordT](self, dataset: Dataset[RecordT], data: BaseModel, recieved_at: datetime) -> None:
        row = pl.DataFrame(
            {**{key: [value] for key, value in data.model_dump().items()}, "recieved_at": [recieved_at]},
            schema_overrides=dataset.schema_overrides,
        )

        path = self._file_path(dataset, recieved_at.astimezone(TZ).date())

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

    def load[RecordT](self, dataset: Dataset[RecordT], start: datetime, end: datetime) -> list[RecordT]:
        # Daily files are bucketed by JST date, so the range of candidate files is
        # derived from the JST dates of the query bounds.
        first_day = start.astimezone(TZ).date()
        last_day = end.astimezone(TZ).date()

        # Reads take the lock too: save() rewrites the whole file, and a concurrent
        # read could otherwise see a partially written parquet file.
        with self._lock:
            frames = []
            day = first_day
            while day <= last_day:
                path = self._file_path(dataset, day)
                if path.exists():
                    frames.append(pl.read_parquet(path))
                day += timedelta(days=1)

        if not frames:
            return []
        df = pl.concat(frames).filter(pl.col("recieved_at").is_between(start, end)).sort("recieved_at")
        # to_dicts() is untyped (list[dict[str, Any]]); the parquet schema guarantees these keys.
        rows = df.to_dicts()
        # Parquet normalizes tz-aware datetimes to UTC; convert back to JST so API
        # responses are consistently in the system timezone.
        for row in rows:
            row["recieved_at"] = row["recieved_at"].astimezone(TZ)
        return cast("list[RecordT]", rows)


# Cached so the whole app shares one instance — and therefore one lock.
@lru_cache(maxsize=1)
def get_storage() -> Storage:
    return Storage(data_dir=get_config().data_dir)
