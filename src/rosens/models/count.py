from typing import Literal, TypedDict
lazy from datetime import datetime

from pydantic import BaseModel, Field

from rosens.models.common import SensorId

# What is being counted. Every count type shares the same row shape, so they all live in one
# dataset and this is just a label column. Add a new type here to start accepting it.
CountType = Literal["motion"]


class CountReading(BaseModel):
    """How many times something happened during one counting period, without sensor identity."""

    count: int = Field(ge=0, description="Number of occurrences during the period")
    duration_s: int = Field(gt=0, description="Length of the counting period in seconds, ending at receipt")


class CountData(CountReading):
    sensor_id: SensorId
    count_type: CountType = Field(description="What is being counted (e.g. motion sensor triggers)")


class CountRecord(TypedDict):
    """A stored count as loaded back from a parquet row (internal, not an API schema)."""

    sensor_id: str
    count_type: CountType
    count: int
    duration_s: int
    received_at: datetime
