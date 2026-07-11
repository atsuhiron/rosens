from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest

from rosens.config import Config
from rosens.models.sensor_data import SensorData
from rosens.storage import save_sensor_data

RECIEVED_AT = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _use_tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("rosens.storage.get_config", lambda: Config(data_dir=tmp_path))


def test_save_sensor_data_creates_new_file(tmp_path: Path) -> None:
    sensor_data = SensorData(sensor_id="sensor-1", temperature=20.0, humidity=40.0, pressure=1000.0)

    save_sensor_data(sensor_data, RECIEVED_AT)

    path = tmp_path / "2026-07-11.parquet"
    assert path.exists()
    df = pl.read_parquet(path)
    assert df["sensor_id"].to_list() == ["sensor-1"]


def test_save_sensor_data_appends_to_existing_file(tmp_path: Path) -> None:
    first = SensorData(sensor_id="sensor-1", temperature=20.0, humidity=40.0, pressure=1000.0)
    second = SensorData(sensor_id="sensor-2", temperature=21.0, humidity=41.0, pressure=1001.0)

    save_sensor_data(first, RECIEVED_AT)
    save_sensor_data(second, RECIEVED_AT)

    path = tmp_path / "2026-07-11.parquet"
    df = pl.read_parquet(path)
    assert df["sensor_id"].to_list() == ["sensor-1", "sensor-2"]
