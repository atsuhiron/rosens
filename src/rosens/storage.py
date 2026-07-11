import threading
from datetime import datetime
from pathlib import Path

import polars as pl

from rosens.config import get_config
from rosens.models.sensor_data import SensorData

_write_lock = threading.Lock()


def _file_path_for(recieved_at: datetime) -> Path:
    return get_config().data_dir / f"{recieved_at:%Y-%m-%d}.parquet"


def save_sensor_data(sensor_data: SensorData, recieved_at: datetime) -> None:
    row = pl.DataFrame(
        {
            "sensor_id": [sensor_data.sensor_id],
            "temperature": [sensor_data.temperature],
            "humidity": [sensor_data.humidity],
            "pressure": [sensor_data.pressure],
            "recieved_at": [recieved_at],
        },
    )

    path = _file_path_for(recieved_at)

    # Parquet has no native append, so the daily file is read, combined with the
    # new row, and rewritten. A process-wide lock keeps concurrent requests
    # (FastAPI runs sync endpoints in a threadpool) from clobbering each other.
    with _write_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            existing = pl.read_parquet(path)
            combined = pl.concat([existing, row])
        else:
            combined = row
        combined.write_parquet(path)
