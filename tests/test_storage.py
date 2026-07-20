from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl

from rosens.datasets import ENVIRONMENT
from rosens.models.environment import EnvironmentData
from rosens.storage import Storage

RECEIVED_AT = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)


def _environment_data(sensor_id: str) -> EnvironmentData:
    return EnvironmentData(sensor_id=sensor_id, temperature=20.0, humidity=40.0, pressure=1000.0, uptime_s=3600)


def test_save_creates_new_file(tmp_path: Path) -> None:
    storage = Storage(data_dir=tmp_path)

    storage.save(ENVIRONMENT, _environment_data("sensor-1"), RECEIVED_AT)

    path = tmp_path / "environment" / "2026-07-11.parquet"
    assert path.exists()
    df = pl.read_parquet(path)
    assert df["sensor_id"].to_list() == ["sensor-1"]
    assert df["uptime_s"].to_list() == [3600]
    assert df["uptime_s"].dtype == pl.Int32
    assert df["temperature"].dtype == pl.Float32
    assert df["humidity"].dtype == pl.Float32
    assert df["pressure"].dtype == pl.Float32


def test_save_appends_to_existing_file(tmp_path: Path) -> None:
    storage = Storage(data_dir=tmp_path)

    storage.save(ENVIRONMENT, _environment_data("sensor-1"), RECEIVED_AT)
    storage.save(ENVIRONMENT, _environment_data("sensor-2"), RECEIVED_AT)

    df = pl.read_parquet(tmp_path / "environment" / "2026-07-11.parquet")
    assert df["sensor_id"].to_list() == ["sensor-1", "sensor-2"]


def test_load_spans_multiple_days(tmp_path: Path) -> None:
    storage = Storage(data_dir=tmp_path)
    times = {
        "day1": datetime(2026, 7, 11, 6, 0, 0, tzinfo=UTC),
        "day2": datetime(2026, 7, 12, 6, 0, 0, tzinfo=UTC),
        "day3": datetime(2026, 7, 13, 6, 0, 0, tzinfo=UTC),
    }
    for sensor_id, received_at in times.items():
        storage.save(ENVIRONMENT, _environment_data(sensor_id), received_at)

    rows = storage.load(ENVIRONMENT, times["day1"], times["day2"])

    assert [row["sensor_id"] for row in rows] == ["day1", "day2"]
    assert rows[0]["received_at"] == times["day1"]
    assert rows[0]["temperature"] == 20.0
    assert rows[0]["uptime_s"] == 3600


def test_load_includes_boundary_timestamps(tmp_path: Path) -> None:
    storage = Storage(data_dir=tmp_path)
    before = RECEIVED_AT - timedelta(hours=2)
    after = RECEIVED_AT + timedelta(hours=2)
    for sensor_id, received_at in [("before", before), ("exact", RECEIVED_AT), ("after", after)]:
        storage.save(ENVIRONMENT, _environment_data(sensor_id), received_at)

    rows = storage.load(ENVIRONMENT, RECEIVED_AT, after)

    assert [row["sensor_id"] for row in rows] == ["exact", "after"]


def test_load_returns_empty_when_no_files(tmp_path: Path) -> None:
    storage = Storage(data_dir=tmp_path)

    rows = storage.load(ENVIRONMENT, RECEIVED_AT, RECEIVED_AT + timedelta(days=1))

    assert rows == []
