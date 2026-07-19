from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from rosens.models.sensor_data import SensorReading


class PingResponse(BaseModel):
    status: Literal["ok"] = Field(description="Status of the API")
    version: str = Field(description="Version of the API")


class RegisterResponse(BaseModel):
    msg: Literal["recieved"] = Field(description="Confirmation message for successful registration")
    recieved_at: datetime = Field(description="Timestamp when the data was received")


class StoredSensorData(SensorReading):
    recieved_at: datetime = Field(description="Timestamp when the data was received")


class SensorSequence(BaseModel):
    sensor_id: str = Field(description="Unique identifier for the sensor")
    sequence: list[StoredSensorData] = Field(description="Readings from this sensor, oldest first")


class GetDataResponse(BaseModel):
    data: list[SensorSequence] = Field(description="Per-sensor readings in the requested period")
