from rosens.downsample import decimate


def test_returns_same_object_when_within_limit() -> None:
    items = [object() for _ in range(5)]
    assert decimate(items, 5) is items
    assert decimate(items, 10) is items


def test_returns_same_object_when_max_points_not_positive() -> None:
    items = [object() for _ in range(5)]
    assert decimate(items, 0) is items
    assert decimate(items, -3) is items


def test_thins_to_at_most_max_points_plus_one() -> None:
    kept = decimate(list(range(10080)), 1000)
    assert len(kept) <= 1001


def test_keeps_first_and_last_point() -> None:
    items = [object() for _ in range(10)]
    kept = decimate(items, 3)
    assert kept[0] is items[0]
    assert kept[-1] is items[-1]


def test_does_not_duplicate_last_when_slice_already_lands_on_it() -> None:
    # range(7)[::3] -> 0, 3, 6; index 6 is already the final element, so no extra append.
    assert decimate(list(range(7)), 3) == [0, 3, 6]


def test_preserves_order_as_subsequence() -> None:
    kept = decimate(list(range(100)), 10)
    assert kept == sorted(kept)
    assert set(kept) <= set(range(100))
    assert kept[0] == 0
    assert kept[-1] == 99
