"""Debug helper: print the contents of one daily parquet file in the data directory.

Usage: uv run python etc/dump_data.py 2026-07-18  (run from the repository root so config.json is found)
"""

import argparse
import sys
from datetime import date

import polars as pl

from rosens.config import get_config


def parse_args() -> date:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("date", type=date.fromisoformat, help="date of the daily file to print (yyyy-mm-dd)")
    return parser.parse_args().date


def main() -> None:
    # Windows consoles default to cp932, which cannot encode polars' box-drawing characters.
    sys.stdout.reconfigure(encoding="utf-8")
    target = parse_args()
    data_dir = get_config().data_dir
    file = data_dir / f"{target.isoformat()}.parquet"
    if not file.exists():
        available = ", ".join(f.stem for f in sorted(data_dir.glob("*.parquet"))) or "(none)"
        sys.exit(f"{file} not found. Available dates: {available}")
    df = pl.read_parquet(file)
    with pl.Config(tbl_rows=-1, tbl_cols=-1, fmt_str_lengths=200):
        print(f"=== {file.name} ({df.height} rows) ===")
        print(df)


if __name__ == "__main__":
    main()
