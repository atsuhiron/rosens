from dataclasses import dataclass, field

import polars as pl

from rosens.models.environment import EnvironmentRecord


@dataclass(frozen=True)
class Dataset[RecordT]:
    """A kind of data rosens stores.

    Bundles what the storage layer needs to know about one data kind: the
    subdirectory it lives in under ``data_dir`` and the parquet column types.
    ``RecordT`` is the TypedDict shape of a row loaded back from parquet.
    """

    name: str
    # Column dtypes forced on write; unlisted columns keep polars' inferred type.
    schema_overrides: dict[str, type[pl.DataType]] = field(default_factory=dict)


ENVIRONMENT = Dataset[EnvironmentRecord](
    name="environment",
    schema_overrides={
        "temperature": pl.Float32,
        "humidity": pl.Float32,
        "pressure": pl.Float32,
        "uptime_s": pl.Int32,
    },
)
