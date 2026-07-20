from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from rosens.models.environment import EnvironmentReading


class PingResponse(BaseModel):
    status: Literal["ok"] = Field(description="Status of the API")
    version: str = Field(description="Version of the API")


class RegisterResponse(BaseModel):
    msg: Literal["recieved"] = Field(description="Confirmation message for successful registration")
    recieved_at: datetime = Field(description="Timestamp when the data was received")


class StoredEnvironmentData(EnvironmentReading):
    recieved_at: datetime = Field(description="Timestamp when the data was received")


class EnvironmentSequence(BaseModel):
    sensor_id: str = Field(description="Unique identifier for the sensor")
    sequence: list[StoredEnvironmentData] = Field(description="Readings from this sensor, oldest first")


class GetEnvironmentDataResponse(BaseModel):
    data: list[EnvironmentSequence] = Field(description="Per-sensor readings in the requested period")
