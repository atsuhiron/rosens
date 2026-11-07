import asyncio
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Annotated

import fastapi

from rosens.bucketing import bucket_counts
from rosens.datasets import COUNT, ENVIRONMENT
from rosens.downsample import decimate
from rosens.models.api_models import (
    CountSequence,
    EnvironmentSequence,
    GetCountDataResponse,
    GetEnvironmentDataResponse,
    PingResponse,
    RegisterResponse,
    StoredCountData,
    StoredEnvironmentData,
)
from rosens.storage import get_storage
from rosens.util import TZ
lazy from rosens.models.count import CountData, CountRecord, CountType
lazy from rosens.models.environment import EnvironmentData, EnvironmentRecord

app = fastapi.FastAPI(
    title="Rosens API",
    version="2.2.0",
)

# Dashboard (static HTML + vendored ECharts). Resolved from the package location so
# it works regardless of the server's working directory.
app.frontend("/ui", directory=str(Path(__file__).parent / "frontend"))


def _resolve_period(start: datetime, end: datetime | None) -> tuple[datetime, datetime]:
    # Naive datetimes are interpreted as JST, the timezone the whole system runs in.
    if start.tzinfo is None:
        start = start.replace(tzinfo=TZ)
    if end is None:
        end = datetime.now(tz=TZ)
    elif end.tzinfo is None:
        end = end.replace(tzinfo=TZ)
    return start, end


def _parse_csv(value: str | None) -> set[str]:
    # Comma-separated; an empty selection (returned as an empty set) means "everything".
    return {part.strip() for part in (value or "").split(",")} - {""}


@app.get("/")
def ping() -> PingResponse:
    return PingResponse(status="ok", version=app.version)


@app.post("/register/environment")
async def register_environment(data: EnvironmentData) -> RegisterResponse:
    now = datetime.now(tz=TZ)
    # save() does blocking file I/O (polars parquet read/write), so it is
    # offloaded to a thread to keep the event loop free for other requests.
    await asyncio.to_thread(get_storage().save, ENVIRONMENT, data, now)
    return RegisterResponse(msg="received", received_at=now)


@app.get("/data/environment")
async def get_environment_data(
    start: datetime,
    end: datetime | None = None,
    max_points: Annotated[int | None, fastapi.Query(gt=0)] = None,
    sensor_ids: str | None = None,
) -> GetEnvironmentDataResponse:
    # New names rather than rebinding start/end: the lambda below would otherwise see the
    # parameters' declared (Optional) types.
    period_start, period_end = _resolve_period(start, end)
    # load() does blocking file I/O, so it is offloaded like the register endpoint.
    # Wrapped in a lambda because ty cannot solve load()'s type variable through to_thread.
    rows = await asyncio.to_thread(lambda: get_storage().load(ENVIRONMENT, period_start, period_end))
    selected = _parse_csv(sensor_ids)
    # Rows arrive sorted by received_at, so each per-sensor sequence stays oldest-first.
    grouped: dict[str, list[EnvironmentRecord]] = defaultdict(list)
    for row in rows:
        if not selected or row["sensor_id"] in selected:
            grouped[row["sensor_id"]].append(row)
    data = []
    for sensor_id, sensor_rows in sorted(grouped.items()):
        # Thin each sensor independently (densities/gaps differ per sensor). Decimating the
        # raw rows before validation avoids validating points we are about to drop.
        kept = decimate(sensor_rows, max_points) if max_points is not None else sensor_rows
        sequence = [StoredEnvironmentData.model_validate(row) for row in kept]
        data.append(EnvironmentSequence(sensor_id=sensor_id, sequence=sequence))
    return GetEnvironmentDataResponse(data=data)


@app.post("/register/count")
async def register_count(data: CountData) -> RegisterResponse:
    now = datetime.now(tz=TZ)
    # Blocking parquet I/O, offloaded to a thread like register_environment.
    await asyncio.to_thread(get_storage().save, COUNT, data, now)
    return RegisterResponse(msg="received", received_at=now)


@app.get("/data/count")
async def get_count_data(
    start: datetime,
    end: datetime | None = None,
    sensor_ids: str | None = None,
    count_types: str | None = None,
    bucket_s: Annotated[int | None, fastapi.Query(gt=0)] = None,
) -> GetCountDataResponse:
    # No max_points here: decimating counts would silently drop occurrences. To shrink long
    # periods, bucket_s sums them into fixed-width buckets instead.
    period_start, period_end = _resolve_period(start, end)
    rows = await asyncio.to_thread(lambda: get_storage().load(COUNT, period_start, period_end))
    selected_sensors = _parse_csv(sensor_ids)
    selected_types = _parse_csv(count_types)
    # Rows arrive sorted by received_at, so each sequence stays oldest-first.
    grouped: dict[tuple[str, CountType], list[CountRecord]] = defaultdict(list)
    for row in rows:
        if selected_sensors and row["sensor_id"] not in selected_sensors:
            continue
        if selected_types and row["count_type"] not in selected_types:
            continue
        grouped[row["sensor_id"], row["count_type"]].append(row)
    data = [
        CountSequence(
            sensor_id=sensor_id,
            count_type=count_type,
            sequence=(
                bucket_counts(group_rows, bucket_s)
                if bucket_s is not None
                else [StoredCountData.model_validate(row) for row in group_rows]
            ),
        )
        for (sensor_id, count_type), group_rows in sorted(grouped.items())
    ]
    return GetCountDataResponse(data=data)
