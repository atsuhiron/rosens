import asyncio
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import fastapi

from rosens.models.api_models import (
    GetDataResponse,
    PingResponse,
    RegisterResponse,
    SensorSequence,
    StoredSensorData,
)
from rosens.models.sensor_data import SensorData
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


@app.post("/register")
async def register(sensor_data: SensorData) -> RegisterResponse:
    now = datetime.now(tz=TZ)
    # save_sensor_data does blocking file I/O (polars parquet read/write), so it is
    # offloaded to a thread to keep the event loop free for other requests.
    await asyncio.to_thread(get_storage().save_sensor_data, sensor_data, now)
    return RegisterResponse(msg="recieved", recieved_at=now)


@app.get("/data")
async def get_data(start: datetime, end: datetime | None = None) -> GetDataResponse:
    # Naive datetimes are interpreted as JST, the timezone the whole system runs in.
    if start.tzinfo is None:
        start = start.replace(tzinfo=TZ)
    if end is None:
        end = datetime.now(tz=TZ)
    elif end.tzinfo is None:
        end = end.replace(tzinfo=TZ)
    # load_sensor_data does blocking file I/O, so it is offloaded like /register.
    rows = await asyncio.to_thread(get_storage().load_sensor_data, start, end)
    # Rows arrive sorted by recieved_at, so each per-sensor sequence stays oldest-first.
    grouped: dict[str, list[StoredSensorData]] = defaultdict(list)
    for row in rows:
        grouped[row["sensor_id"]].append(StoredSensorData.model_validate(row))
    return GetDataResponse(
        data=[
            SensorSequence(sensor_id=sensor_id, sequence=sequence) for sensor_id, sequence in sorted(grouped.items())
        ]
    )
