from datetime import datetime

import pytest

from rosens.api import register
from rosens.models.sensor_data import SensorData


class FakeStorage:
    def __init__(self) -> None:
        self.calls: list[tuple[SensorData, datetime]] = []

    def save_sensor_data(self, sensor_data: SensorData, recieved_at: datetime) -> None:
        self.calls.append((sensor_data, recieved_at))


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
