from datetime import datetime

import pytest

from rosens.api import register
from rosens.models.sensor_data import SensorData


@pytest.mark.asyncio
async def test_register_calls_save_sensor_data(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[SensorData, datetime]] = []

    def fake_save_sensor_data(sensor_data: SensorData, recieved_at: datetime) -> None:
        calls.append((sensor_data, recieved_at))

    monkeypatch.setattr("rosens.api.save_sensor_data", fake_save_sensor_data)

    sensor_data = SensorData(sensor_id="sensor-1", temperature=23.5, humidity=45.2, pressure=1013.2)

    response = await register(sensor_data)

    assert response.msg == "recieved"
    assert len(calls) == 1
    saved_sensor_data, saved_recieved_at = calls[0]
    assert saved_sensor_data == sensor_data
    assert saved_recieved_at == response.recieved_at
