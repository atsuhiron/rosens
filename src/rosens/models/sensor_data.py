from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel, Field


class SensorReading(BaseModel):
    """Measured values of a single reading, without sensor identity."""

    temperature: float = Field(description="Temperature in Celsius")
    humidity: float = Field(description="Humidity in percentage")
    pressure: float = Field(description="Atmospheric pressure in hPa")
    uptime_s: int = Field(description="Uptime of the sensor in seconds")


class SensorData(SensorReading):
    sensor_id: str = Field(description="Unique identifier for the sensor")


class SensorRecord(TypedDict):
    """A stored reading as loaded back from a parquet row (internal, not an API schema)."""

    sensor_id: str
    temperature: float
    humidity: float
    pressure: float
    uptime_s: int
    recieved_at: datetime
