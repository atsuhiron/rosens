from typing import TypedDict
lazy from datetime import datetime

from pydantic import BaseModel, Field


class EnvironmentReading(BaseModel):
    """Measured values of a single reading, without sensor identity.

    Every value is optional because sensors differ in what they can measure: a value the
    sensor does not provide is sent as null or omitted, and is treated as invalid.
    """

    temperature: float | None = Field(default=None, description="Temperature in Celsius, null if not measured")
    humidity: float | None = Field(default=None, description="Humidity in percentage, null if not measured")
    pressure: float | None = Field(default=None, description="Atmospheric pressure in hPa, null if not measured")
    uptime_s: int | None = Field(default=None, description="Uptime of the sensor in seconds, null if not reported")


class EnvironmentData(EnvironmentReading):
    # Limited to URL-unreserved characters: ids go into /ui?sensor_ids=a,b as they are.
    sensor_id: str = Field(pattern=r"^[A-Za-z0-9._~-]+$", description="Unique identifier for the sensor")


class EnvironmentRecord(TypedDict):
    """A stored reading as loaded back from a parquet row (internal, not an API schema)."""

    sensor_id: str
    temperature: float | None
    humidity: float | None
    pressure: float | None
    uptime_s: int | None
    received_at: datetime
