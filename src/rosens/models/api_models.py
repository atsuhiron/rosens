from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PingResponse(BaseModel):
    status: Literal["ok"] = Field(description="Status of the API")
    version: str = Field(description="Version of the API")


class RegisterResponse(BaseModel):
    msg: Literal["recieved"] = Field(description="Confirmation message for successful registration")
    recieved_at: datetime = Field(description="Timestamp when the data was received")
