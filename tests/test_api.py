from datetime import datetime

import pytest
from pydantic import BaseModel

from rosens.api import get_environment_data, register_environment
from rosens.datasets import Dataset
from rosens.models.environment import EnvironmentData, EnvironmentRecord
from rosens.util import TZ


class FakeStorage:
    def __init__(self, rows: list[EnvironmentRecord] | None = None) -> None:
        self.calls: list[tuple[Dataset, BaseModel, datetime]] = []
        self.rows = rows or []

    def save(self, dataset: Dataset, data: BaseModel, recieved_at: datetime) -> None:
        self.calls.append((dataset, data, recieved_at))

    def load[RecordT](self, dataset: Dataset[RecordT], start: datetime, end: datetime) -> list[EnvironmentRecord]:  # noqa: ARG002
        return self.rows


def _row(sensor_id: str, temperature: float, recieved_at: datetime) -> EnvironmentRecord:
    return {
        "sensor_id": sensor_id,
        "temperature": temperature,
        "humidity": 40.0,
        "pressure": 1000.0,
        "uptime_s": 60,
        "recieved_at": recieved_at,
    }


@pytest.mark.asyncio
async def test_register_environment_saves_to_environment_dataset(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_storage = FakeStorage()
    monkeypatch.setattr("rosens.api.get_storage", lambda: fake_storage)

    data = EnvironmentData(sensor_id="sensor-1", temperature=23.5, humidity=45.2, pressure=1013.2, uptime_s=3600)

    response = await register_environment(data)

    assert response.msg == "recieved"
    assert len(fake_storage.calls) == 1
    saved_dataset, saved_data, saved_recieved_at = fake_storage.calls[0]
    assert saved_dataset.name == "environment"
    assert saved_data == data
    assert saved_recieved_at == response.recieved_at


@pytest.mark.asyncio
async def test_get_environment_data_groups_rows_by_sensor(monkeypatch: pytest.MonkeyPatch) -> None:
    t1 = datetime(2026, 7, 19, 10, 0, 0, tzinfo=TZ)
    t2 = datetime(2026, 7, 19, 11, 0, 0, tzinfo=TZ)
    # Rows come from storage sorted by recieved_at, interleaved across sensors.
    fake_storage = FakeStorage(
        rows=[
            _row("s-02", 21.0, t1),
            _row("s-01", 20.0, t1),
            _row("s-01", 20.5, t2),
        ]
    )
    monkeypatch.setattr("rosens.api.get_storage", lambda: fake_storage)

    response = await get_environment_data(start=t1)

    assert [sequence.sensor_id for sequence in response.data] == ["s-01", "s-02"]
    s01 = response.data[0]
    assert [reading.temperature for reading in s01.sequence] == [20.0, 20.5]
    assert [reading.recieved_at for reading in s01.sequence] == [t1, t2]
    assert not hasattr(s01.sequence[0], "sensor_id")
