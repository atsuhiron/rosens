import asyncio
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Annotated

import fastapi

from rosens.datasets import ENVIRONMENT
from rosens.downsample import decimate
from rosens.models.api_models import (
    EnvironmentSequence,
    GetEnvironmentDataResponse,
    PingResponse,
    RegisterResponse,
    StoredEnvironmentData,
)
from rosens.models.environment import EnvironmentData, EnvironmentRecord
from rosens.storage import get_storage
from rosens.util import TZ

app = fastapi.FastAPI(
    title="Rosens API",
    version="1.0.0",
)

# Dashboard (static HTML + vendored ECharts). Resolved from the package location so
# it works regardless of the server's working directory.
app.frontend("/ui", directory=str(Path(__file__).parent / "frontend"))


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
) -> GetEnvironmentDataResponse:
    # Naive datetimes are interpreted as JST, the timezone the whole system runs in.
    if start.tzinfo is None:
        start = start.replace(tzinfo=TZ)
    if end is None:
        end = datetime.now(tz=TZ)
    elif end.tzinfo is None:
        end = end.replace(tzinfo=TZ)
    # load() does blocking file I/O, so it is offloaded like the register endpoint.
    # Wrapped in a lambda because ty cannot solve load()'s type variable through to_thread.
    query_end = end
    rows = await asyncio.to_thread(lambda: get_storage().load(ENVIRONMENT, start, query_end))
    # Rows arrive sorted by received_at, so each per-sensor sequence stays oldest-first.
    grouped: dict[str, list[EnvironmentRecord]] = defaultdict(list)
    for row in rows:
        grouped[row["sensor_id"]].append(row)
    data = []
    for sensor_id, sensor_rows in sorted(grouped.items()):
        # Thin each sensor independently (densities/gaps differ per sensor). Decimating the
        # raw rows before validation avoids validating points we are about to drop.
        kept = decimate(sensor_rows, max_points) if max_points is not None else sensor_rows
        sequence = [StoredEnvironmentData.model_validate(row) for row in kept]
        data.append(EnvironmentSequence(sensor_id=sensor_id, sequence=sequence))
    return GetEnvironmentDataResponse(data=data)
