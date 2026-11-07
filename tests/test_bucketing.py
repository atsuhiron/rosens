from datetime import datetime

from rosens.bucketing import bucket_counts
from rosens.util import TZ
lazy from rosens.models.count import CountRecord

HOUR = 3600


def _row(received_at: datetime, count: int, duration_s: int = 300) -> CountRecord:
    return {
        "sensor_id": "s-01",
        "count_type": "motion",
        "count": count,
        "duration_s": duration_s,
        "received_at": received_at,
    }


def _jst(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 7, day, hour, minute, tzinfo=TZ)


def test_sums_rows_in_the_same_bucket() -> None:
    rows = [_row(_jst(19, 10, 10), 2), _row(_jst(19, 10, 30), 3), _row(_jst(19, 10, 50), 4)]

    buckets = bucket_counts(rows, HOUR)

    assert [(b.received_at, b.count) for b in buckets] == [(_jst(19, 11), 9)]


def test_splits_rows_into_separate_buckets_oldest_first() -> None:
    rows = [_row(_jst(19, 12, 30), 1), _row(_jst(19, 10, 30), 2), _row(_jst(19, 13, 30), 3)]

    buckets = bucket_counts(rows, HOUR)

    assert [(b.received_at, b.count) for b in buckets] == [
        (_jst(19, 11), 2),
        (_jst(19, 13), 1),
        (_jst(19, 14), 3),
    ]


def test_assigns_by_middle_of_the_counting_window() -> None:
    # 11:57-12:02 has its middle at 11:59:30, so it belongs to the 11:00-12:00 bucket.
    assert bucket_counts([_row(_jst(19, 12, 2), 5)], HOUR)[0].received_at == _jst(19, 12)
    # A window ending exactly on the hour (11:55-12:00) too.
    assert bucket_counts([_row(_jst(19, 12, 0), 5)], HOUR)[0].received_at == _jst(19, 12)
    # 12:00-12:05 has its middle at 12:02:30: the next bucket.
    assert bucket_counts([_row(_jst(19, 12, 5), 5)], HOUR)[0].received_at == _jst(19, 13)


def test_aligns_buckets_to_jst_midnight() -> None:
    rows = [_row(_jst(19, hour, 30), 1) for hour in (1, 7, 13, 19)]

    buckets = bucket_counts(rows, 6 * HOUR)

    assert [b.received_at for b in buckets] == [_jst(19, 6), _jst(19, 12), _jst(19, 18), _jst(20, 0)]


def test_reports_bucket_width_as_duration() -> None:
    # 10:30-10:31, middle 10:30:30: the 10:30-10:45 bucket.
    buckets = bucket_counts([_row(_jst(19, 10, 31), 1, duration_s=60)], 900)

    assert buckets[0].duration_s == 900
    assert buckets[0].received_at == _jst(19, 10, 45)


def test_keeps_buckets_with_zero_count() -> None:
    assert [b.count for b in bucket_counts([_row(_jst(19, 10, 30), 0)], HOUR)] == [0]


def test_returns_empty_for_no_rows() -> None:
    assert bucket_counts([], HOUR) == []
