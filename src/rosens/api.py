import asyncio
from datetime import datetime

import fastapi

from rosens.models.api_models import PingResponse, RegisterResponse
from rosens.models.sensor_data import SensorData
from rosens.storage import get_storage
from rosens.util import TZ

app = fastapi.FastAPI(
    title="Rosens API",
    version="0.1.0",
)


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
