from collections import defaultdict
from datetime import datetime, timedelta

from rosens.models.api_models import StoredCountData
from rosens.util import TZ
lazy from rosens.models.count import CountRecord

# Buckets are aligned to JST midnight (a 6h bucket starts at 0/6/12/18 JST).
_ORIGIN = datetime(1970, 1, 1, tzinfo=TZ)


def bucket_counts(rows: list[CountRecord], bucket_s: int) -> list[StoredCountData]:
    """Sum counts into fixed ``bucket_s``-second buckets, oldest bucket first.

    Each row covers the ``duration_s`` seconds ending at its ``received_at`` and is assigned
    to the bucket holding the middle of that window, so a 11:55-12:00 window counts towards
    11:00-12:00 rather than the next hour. A bucket is returned in the same shape as a raw
    count: ``duration_s`` is ``bucket_s`` and ``received_at`` is the end of the bucket (in
    the future for the bucket still in progress). Buckets without any row are omitted.

    ``rows`` are expected to come from one sensor and one count type.
    """
    width = timedelta(seconds=bucket_s)
    totals: dict[datetime, int] = defaultdict(int)
    for row in rows:
        middle = row["received_at"] - timedelta(seconds=row["duration_s"]) / 2
        bucket_start = _ORIGIN + (middle - _ORIGIN) // width * width
        totals[bucket_start + width] += row["count"]
    return [
        StoredCountData(count=count, duration_s=bucket_s, received_at=end) for end, count in sorted(totals.items())
    ]
