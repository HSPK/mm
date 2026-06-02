from __future__ import annotations

from mm.utils.parallel import map_items


def _square(value: int) -> int:
    return value * value


def test_map_items_thread_backend():
    seen: list[int] = []

    results = map_items(
        _square,
        [1, 2, 3],
        backend="thread",
        on_result=seen.append,
    )

    assert sorted(results) == [1, 4, 9]
    assert sorted(seen) == [1, 4, 9]


def test_map_items_sequential_backend_preserves_order():
    seen: list[int] = []

    results = map_items(
        _square,
        [3, 1, 2],
        backend="sequential",
        on_result=seen.append,
    )

    assert results == [9, 1, 4]
    assert seen == [9, 1, 4]


def test_map_items_empty_input():
    assert map_items(_square, [], backend="thread") == []
