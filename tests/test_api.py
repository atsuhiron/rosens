from datetime import datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError
lazy from pydantic import BaseModel

from rosens.api import get_count_data, get_environment_data, register_count, register_environment
from rosens.models.count import CountData, CountRecord, CountType
from rosens.models.environment import EnvironmentData, EnvironmentRecord
from rosens.util import TZ
lazy from rosens.datasets import Dataset


class FakeStorage:
    def __init__(self, rows: list[Any] | None = None) -> None:
        self.calls: list[tuple[Dataset, BaseModel, datetime]] = []
        self.rows = rows or []

    def save(self, dataset: Dataset, data: BaseModel, received_at: datetime) -> None:
        self.calls.append((dataset, data, received_at))

    def load[RecordT](self, dataset: Dataset[RecordT], start: datetime, end: datetime) -> list[Any]:  # noqa: ARG002
        return self.rows


def _row(sensor_id: str, temperature: float, received_at: datetime) -> EnvironmentRecord:
    return {
        "sensor_id": sensor_id,
        "temperature": temperature,
        "humidity": 40.0,
        "pressure": 1000.0,
        "uptime_s": 60,
        "received_at": received_at,
    }


@pytest.mark.asyncio
async def test_register_environment_saves_to_environment_dataset(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_storage = FakeStorage()
    monkeypatch.setattr("rosens.api.get_storage", lambda: fake_storage)

    data = EnvironmentData(sensor_id="sensor-1", temperature=23.5, humidity=45.2, pressure=1013.2, uptime_s=3600)

    response = await register_environment(data)

    assert response.msg == "received"
    assert len(fake_storage.calls) == 1
    saved_dataset, saved_data, saved_received_at = fake_storage.calls[0]
    assert saved_dataset.name == "environment"
    assert saved_data == data
    assert saved_received_at == response.received_at


@pytest.mark.asyncio
async def test_get_environment_data_groups_rows_by_sensor(monkeypatch: pytest.MonkeyPatch) -> None:
    t1 = datetime(2026, 7, 19, 10, 0, 0, tzinfo=TZ)
    t2 = datetime(2026, 7, 19, 11, 0, 0, tzinfo=TZ)
    # Rows come from storage sorted by received_at, interleaved across sensors.
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
    assert [reading.received_at for reading in s01.sequence] == [t1, t2]
    assert not hasattr(s01.sequence[0], "sensor_id")


@pytest.mark.asyncio
async def test_get_environment_data_downsamples_when_max_points_given(monkeypatch: pytest.MonkeyPatch) -> None:
    base = datetime(2026, 7, 19, 0, 0, 0, tzinfo=TZ)
    rows = [_row("s-01", float(i), base + timedelta(minutes=i)) for i in range(1000)]
    fake_storage = FakeStorage(rows=rows)
    monkeypatch.setattr("rosens.api.get_storage", lambda: fake_storage)

    response = await get_environment_data(start=base, max_points=100)

    sequence = response.data[0].sequence
    assert len(sequence) <= 101
    # First and last readings are preserved so the line still spans the whole period.
    assert sequence[0].received_at == rows[0]["received_at"]
    assert sequence[-1].received_at == rows[-1]["received_at"]


@pytest.mark.asyncio
async def test_get_environment_data_returns_all_points_without_max_points(monkeypatch: pytest.MonkeyPatch) -> None:
    base = datetime(2026, 7, 19, 0, 0, 0, tzinfo=TZ)
    rows = [_row("s-01", float(i), base + timedelta(minutes=i)) for i in range(1000)]
    fake_storage = FakeStorage(rows=rows)
    monkeypatch.setattr("rosens.api.get_storage", lambda: fake_storage)

    response = await get_environment_data(start=base)

    assert len(response.data[0].sequence) == 1000


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sensor_ids", "expected"),
    [
        ("s-01", ["s-01"]),
        ("s-01,s-03", ["s-01", "s-03"]),
        (" s-01, s-03 ,", ["s-01", "s-03"]),
        ("s-01,unknown", ["s-01"]),
        ("unknown", []),
        (None, ["s-01", "s-02", "s-03"]),
        ("", ["s-01", "s-02", "s-03"]),
        (",", ["s-01", "s-02", "s-03"]),
    ],
)
async def test_get_environment_data_selects_sensors(
    monkeypatch: pytest.MonkeyPatch, sensor_ids: str | None, expected: list[str]
) -> None:
    t = datetime(2026, 7, 19, 10, 0, 0, tzinfo=TZ)
    fake_storage = FakeStorage(rows=[_row("s-01", 20.0, t), _row("s-02", 21.0, t), _row("s-03", 22.0, t)])
    monkeypatch.setattr("rosens.api.get_storage", lambda: fake_storage)

    response = await get_environment_data(start=t, sensor_ids=sensor_ids)

    assert [sequence.sensor_id for sequence in response.data] == expected


@pytest.mark.asyncio
async def test_get_environment_data_returns_null_values_as_none(monkeypatch: pytest.MonkeyPatch) -> None:
    t = datetime(2026, 7, 19, 10, 0, 0, tzinfo=TZ)
    row: EnvironmentRecord = {**_row("s-01", 20.0, t), "pressure": None, "uptime_s": None}
    fake_storage = FakeStorage(rows=[row])
    monkeypatch.setattr("rosens.api.get_storage", lambda: fake_storage)

    response = await get_environment_data(start=t)

    reading = response.data[0].sequence[0]
    assert reading.temperature == 20.0
    assert reading.pressure is None
    assert reading.uptime_s is None


def test_environment_data_omitted_values_are_none() -> None:
    data = EnvironmentData(sensor_id="s-01")

    assert data.temperature is None
    assert data.humidity is None
    assert data.pressure is None
    assert data.uptime_s is None


def test_environment_data_accepts_explicit_null() -> None:
    data = EnvironmentData.model_validate({"sensor_id": "s-01", "temperature": 20.0, "humidity": None})

    assert data.temperature == 20.0
    assert data.humidity is None


def _environment_data(sensor_id: str) -> EnvironmentData:
    return EnvironmentData(sensor_id=sensor_id, temperature=20.0, humidity=40.0, pressure=1000.0, uptime_s=60)


@pytest.mark.parametrize("sensor_id", ["home_1", "a.b~c-1", "A9"])
def test_environment_data_accepts_url_unreserved_sensor_id(sensor_id: str) -> None:
    assert _environment_data(sensor_id).sensor_id == sensor_id


@pytest.mark.parametrize("sensor_id", ["", "a,b", "home 1", "a/b", "日本語", "home_1\n"])
def test_environment_data_rejects_other_sensor_id(sensor_id: str) -> None:
    with pytest.raises(ValidationError):
        _environment_data(sensor_id)


def _count_row(sensor_id: str, count_type: CountType, count: int, received_at: datetime) -> CountRecord:
    return {
        "sensor_id": sensor_id,
        "count_type": count_type,
        "count": count,
        "duration_s": 300,
        "received_at": received_at,
    }


@pytest.mark.asyncio
async def test_register_count_saves_to_count_dataset(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_storage = FakeStorage()
    monkeypatch.setattr("rosens.api.get_storage", lambda: fake_storage)

    data = CountData(sensor_id="sensor-1", count_type="motion", count=12, duration_s=300)

    response = await register_count(data)

    assert response.msg == "received"
    assert len(fake_storage.calls) == 1
    saved_dataset, saved_data, saved_received_at = fake_storage.calls[0]
    assert saved_dataset.name == "count"
    assert saved_data == data
    assert saved_received_at == response.received_at


@pytest.mark.asyncio
async def test_get_count_data_groups_rows_by_sensor_and_type(monkeypatch: pytest.MonkeyPatch) -> None:
    t1 = datetime(2026, 7, 19, 10, 0, 0, tzinfo=TZ)
    t2 = datetime(2026, 7, 19, 10, 5, 0, tzinfo=TZ)
    fake_storage = FakeStorage(
        rows=[
            _count_row("s-02", "motion", 1, t1),
            _count_row("s-01", "motion", 3, t1),
            _count_row("s-01", "motion", 0, t2),
        ]
    )
    monkeypatch.setattr("rosens.api.get_storage", lambda: fake_storage)

    response = await get_count_data(start=t1)

    assert [(s.sensor_id, s.count_type) for s in response.data] == [("s-01", "motion"), ("s-02", "motion")]
    s01 = response.data[0]
    assert [c.count for c in s01.sequence] == [3, 0]
    assert [c.duration_s for c in s01.sequence] == [300, 300]
    assert [c.received_at for c in s01.sequence] == [t1, t2]
    assert not hasattr(s01.sequence[0], "sensor_id")
    assert not hasattr(s01.sequence[0], "count_type")


@pytest.mark.asyncio
async def test_get_count_data_sums_each_group_into_buckets(monkeypatch: pytest.MonkeyPatch) -> None:
    def at(hour: int, minute: int) -> datetime:
        return datetime(2026, 7, 19, hour, minute, 0, tzinfo=TZ)

    fake_storage = FakeStorage(
        rows=[
            _count_row("s-01", "motion", 1, at(10, 10)),
            _count_row("s-02", "motion", 5, at(10, 20)),
            _count_row("s-01", "motion", 2, at(10, 40)),
            _count_row("s-01", "motion", 4, at(11, 30)),
        ]
    )
    monkeypatch.setattr("rosens.api.get_storage", lambda: fake_storage)

    response = await get_count_data(start=at(10, 0), bucket_s=3600)

    s01, s02 = response.data
    assert [(c.received_at, c.count, c.duration_s) for c in s01.sequence] == [
        (at(11, 0), 3, 3600),
        (at(12, 0), 4, 3600),
    ]
    assert [(c.received_at, c.count) for c in s02.sequence] == [(at(11, 0), 5)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sensor_ids", "count_types", "expected"),
    [
        (None, None, ["s-01", "s-02"]),
        ("s-01", None, ["s-01"]),
        (" s-01, unknown ,", None, ["s-01"]),
        (None, "motion", ["s-01", "s-02"]),
        (None, "unknown", []),
        ("s-02", "motion", ["s-02"]),
    ],
)
async def test_get_count_data_selects_sensors_and_types(
    monkeypatch: pytest.MonkeyPatch, sensor_ids: str | None, count_types: str | None, expected: list[str]
) -> None:
    t = datetime(2026, 7, 19, 10, 0, 0, tzinfo=TZ)
    fake_storage = FakeStorage(rows=[_count_row("s-01", "motion", 1, t), _count_row("s-02", "motion", 2, t)])
    monkeypatch.setattr("rosens.api.get_storage", lambda: fake_storage)

    response = await get_count_data(start=t, sensor_ids=sensor_ids, count_types=count_types)

    assert [sequence.sensor_id for sequence in response.data] == expected


@pytest.mark.parametrize(
    "overrides",
    [
        {"count_type": "door"},
        {"count_type": None},
        {"count": -1},
        {"duration_s": 0},
        {"sensor_id": "a,b"},
    ],
)
def test_count_data_rejects_invalid_values(overrides: dict[str, object]) -> None:
    payload = {"sensor_id": "s-01", "count_type": "motion", "count": 1, "duration_s": 300, **overrides}
    with pytest.raises(ValidationError):
        CountData.model_validate(payload)


@pytest.mark.parametrize("missing", ["sensor_id", "count_type", "count", "duration_s"])
def test_count_data_requires_every_field(missing: str) -> None:
    payload = {"sensor_id": "s-01", "count_type": "motion", "count": 1, "duration_s": 300}
    del payload[missing]
    with pytest.raises(ValidationError):
        CountData.model_validate(payload)


def test_count_data_accepts_zero_count() -> None:
    assert CountData(sensor_id="s-01", count_type="motion", count=0, duration_s=60).count == 0
