from typing import Annotated

from pydantic import Field

# Limited to URL-unreserved characters: ids go into /ui?sensor_ids=a,b as they are.
SensorId = Annotated[str, Field(pattern=r"^[A-Za-z0-9._~-]+$", description="Unique identifier for the sensor")]
