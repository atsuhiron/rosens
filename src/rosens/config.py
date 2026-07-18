from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

CONFIG_PATH = Path("config.json")


class Config(BaseModel):
    data_dir: Path = Field(default=Path("data"), description="Directory where sensor data parquet files are stored")


@lru_cache(maxsize=1)
def get_config() -> Config:
    if not CONFIG_PATH.exists():
        return Config()
    # utf-8-sig tolerates the BOM that Windows editors (Notepad, PowerShell) often prepend.
    return Config.model_validate_json(CONFIG_PATH.read_text(encoding="utf-8-sig"))
