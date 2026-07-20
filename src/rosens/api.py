import asyncio
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import fastapi

from rosens.datasets import ENVIRONMENT
from rosens.models.api_models import (
    EnvironmentSequence,
    GetEnvironmentDataResponse,
    PingResponse,
    RegisterResponse,
    StoredEnvironmentData,
)
from rosens.models.environment import EnvironmentData
from rosens.storage import get_storage
from rosens.util import TZ

app = fastapi.FastAPI(
    title="Rosens API",
    version="0.1.0",
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
async def get_environment_data(start: datetime, end: datetime | None = None) -> GetEnvironmentDataResponse:
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
    grouped: dict[str, list[StoredEnvironmentData]] = defaultdict(list)
    for row in rows:
        grouped[row["sensor_id"]].append(StoredEnvironmentData.model_validate(row))
    return GetEnvironmentDataResponse(
        data=[
            EnvironmentSequence(sensor_id=sensor_id, sequence=sequence)
            for sensor_id, sequence in sorted(grouped.items())
        ]
    )
