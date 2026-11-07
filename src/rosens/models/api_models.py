from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from rosens.models.count import CountReading, CountType
from rosens.models.environment import EnvironmentReading


class PingResponse(BaseModel):
    status: Literal["ok"] = Field(description="Status of the API")
    version: str = Field(description="Version of the API")


class RegisterResponse(BaseModel):
    msg: Literal["received"] = Field(description="Confirmation message for successful registration")
    received_at: datetime = Field(description="Timestamp when the data was received")


class StoredEnvironmentData(EnvironmentReading):
    received_at: datetime = Field(description="Timestamp when the data was received")


class EnvironmentSequence(BaseModel):
    sensor_id: str = Field(description="Unique identifier for the sensor")
    sequence: list[StoredEnvironmentData] = Field(description="Readings from this sensor, oldest first")


class GetEnvironmentDataResponse(BaseModel):
    data: list[EnvironmentSequence] = Field(description="Per-sensor readings in the requested period")


class StoredCountData(CountReading):
    received_at: datetime = Field(description="Timestamp when the data was received (end of the counting period)")


class CountSequence(BaseModel):
    sensor_id: str = Field(description="Unique identifier for the sensor")
    count_type: CountType = Field(description="What is being counted")
    sequence: list[StoredCountData] = Field(description="Counts of this type from this sensor, oldest first")


class GetCountDataResponse(BaseModel):
    data: list[CountSequence] = Field(description="Per-sensor, per-type counts in the requested period")
