from datetime import datetime

import pytest

from rosens.api import get_data, register
from rosens.models.sensor_data import SensorData, SensorRecord
from rosens.util import TZ


class FakeStorage:
    def __init__(self, rows: list[SensorRecord] | None = None) -> None:
        self.calls: list[tuple[SensorData, datetime]] = []
        self.rows = rows or []

    def save_sensor_data(self, sensor_data: SensorData, recieved_at: datetime) -> None:
        self.calls.append((sensor_data, recieved_at))

    def load_sensor_data(self, start: datetime, end: datetime) -> list[SensorRecord]:  # noqa: ARG002
        return self.rows


def _row(sensor_id: str, temperature: float, recieved_at: datetime) -> SensorRecord:
    return {
        "sensor_id": sensor_id,
        "temperature": temperature,
        "humidity": 40.0,
        "pressure": 1000.0,
        "uptime_s": 60,
        "recieved_at": recieved_at,
    }


@pytest.mark.asyncio
async def test_register_calls_save_sensor_data(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_storage = FakeStorage()
    monkeypatch.setattr("rosens.api.get_storage", lambda: fake_storage)

    sensor_data = SensorData(sensor_id="sensor-1", temperature=23.5, humidity=45.2, pressure=1013.2, uptime_s=3600)

    response = await register(sensor_data)

    assert response.msg == "recieved"
    assert len(fake_storage.calls) == 1
    saved_sensor_data, saved_recieved_at = fake_storage.calls[0]
    assert saved_sensor_data == sensor_data
    assert saved_recieved_at == response.recieved_at


@pytest.mark.asyncio
async def test_get_data_groups_rows_by_sensor(monkeypatch: pytest.MonkeyPatch) -> None:
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

    response = await get_data(start=t1)

    assert [sequence.sensor_id for sequence in response.data] == ["s-01", "s-02"]
    s01 = response.data[0]
    assert [reading.temperature for reading in s01.sequence] == [20.0, 20.5]
    assert [reading.recieved_at for reading in s01.sequence] == [t1, t2]
    assert not hasattr(s01.sequence[0], "sensor_id")
