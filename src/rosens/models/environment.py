from typing import TypedDict
lazy from datetime import datetime

from pydantic import BaseModel, Field


class EnvironmentReading(BaseModel):
    """Measured values of a single reading, without sensor identity."""

    temperature: float = Field(description="Temperature in Celsius")
    humidity: float = Field(description="Humidity in percentage")
    pressure: float = Field(description="Atmospheric pressure in hPa")
    uptime_s: int = Field(description="Uptime of the sensor in seconds")


class EnvironmentData(EnvironmentReading):
    # Limited to URL-unreserved characters: ids go into /ui?sensor_ids=a,b as they are.
    sensor_id: str = Field(pattern=r"^[A-Za-z0-9._~-]+$", description="Unique identifier for the sensor")


class EnvironmentRecord(TypedDict):
    """A stored reading as loaded back from a parquet row (internal, not an API schema)."""

    sensor_id: str
    temperature: float
    humidity: float
    pressure: float
    uptime_s: int
    received_at: datetime
