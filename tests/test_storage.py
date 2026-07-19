from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl

from rosens.models.sensor_data import SensorData
from rosens.storage import Storage

RECIEVED_AT = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)


def test_save_sensor_data_creates_new_file(tmp_path: Path) -> None:
    storage = Storage(data_dir=tmp_path)
    sensor_data = SensorData(sensor_id="sensor-1", temperature=20.0, humidity=40.0, pressure=1000.0, uptime_s=3600)

    storage.save_sensor_data(sensor_data, RECIEVED_AT)

    path = tmp_path / "2026-07-11.parquet"
    assert path.exists()
    df = pl.read_parquet(path)
    assert df["sensor_id"].to_list() == ["sensor-1"]
    assert df["uptime_s"].to_list() == [3600]
    assert df["uptime_s"].dtype == pl.Int32
    assert df["temperature"].dtype == pl.Float32
    assert df["humidity"].dtype == pl.Float32
    assert df["pressure"].dtype == pl.Float32


def test_save_sensor_data_appends_to_existing_file(tmp_path: Path) -> None:
    storage = Storage(data_dir=tmp_path)
    first = SensorData(sensor_id="sensor-1", temperature=20.0, humidity=40.0, pressure=1000.0, uptime_s=3600)
    second = SensorData(sensor_id="sensor-2", temperature=21.0, humidity=41.0, pressure=1001.0, uptime_s=3600)

    storage.save_sensor_data(first, RECIEVED_AT)
    storage.save_sensor_data(second, RECIEVED_AT)

    path = tmp_path / "2026-07-11.parquet"
    df = pl.read_parquet(path)
    assert df["sensor_id"].to_list() == ["sensor-1", "sensor-2"]


def _sensor_data(sensor_id: str) -> SensorData:
    return SensorData(sensor_id=sensor_id, temperature=20.0, humidity=40.0, pressure=1000.0, uptime_s=3600)


def test_load_sensor_data_spans_multiple_days(tmp_path: Path) -> None:
    storage = Storage(data_dir=tmp_path)
    times = {
        "day1": datetime(2026, 7, 11, 6, 0, 0, tzinfo=UTC),
        "day2": datetime(2026, 7, 12, 6, 0, 0, tzinfo=UTC),
        "day3": datetime(2026, 7, 13, 6, 0, 0, tzinfo=UTC),
    }
    for sensor_id, recieved_at in times.items():
        storage.save_sensor_data(_sensor_data(sensor_id), recieved_at)

    rows = storage.load_sensor_data(times["day1"], times["day2"])

    assert [row["sensor_id"] for row in rows] == ["day1", "day2"]
    assert rows[0]["recieved_at"] == times["day1"]
    assert rows[0]["temperature"] == 20.0
    assert rows[0]["uptime_s"] == 3600


def test_load_sensor_data_includes_boundary_timestamps(tmp_path: Path) -> None:
    storage = Storage(data_dir=tmp_path)
    before = RECIEVED_AT - timedelta(hours=2)
    after = RECIEVED_AT + timedelta(hours=2)
    for sensor_id, recieved_at in [("before", before), ("exact", RECIEVED_AT), ("after", after)]:
        storage.save_sensor_data(_sensor_data(sensor_id), recieved_at)

    rows = storage.load_sensor_data(RECIEVED_AT, after)

    assert [row["sensor_id"] for row in rows] == ["exact", "after"]


def test_load_sensor_data_returns_empty_when_no_files(tmp_path: Path) -> None:
    storage = Storage(data_dir=tmp_path)

    rows = storage.load_sensor_data(RECIEVED_AT, RECIEVED_AT + timedelta(days=1))

    assert rows == []
