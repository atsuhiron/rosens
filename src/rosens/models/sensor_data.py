from pydantic import BaseModel, Field


class SensorData(BaseModel):
    sensor_id: str = Field(description="Unique identifier for the sensor")
    temperature: float = Field(description="Temperature in Celsius")
    humidity: float = Field(description="Humidity in percentage")
    pressure: float = Field(description="Atmospheric pressure in hPa")
    uptime_s: int = Field(description="Uptime of the sensor in seconds")
