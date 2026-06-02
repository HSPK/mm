"""Lightweight parallel mapping helpers."""

from __future__ import annotations

import multiprocessing as mp
from collections.abc import Callable, Iterable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Literal, TypeVar

T = TypeVar("T")
R = TypeVar("R")
MapBackend = Literal["process", "thread", "sequential"]


def map_items(
    fn: Callable[[T], R],
    items: Iterable[T],
    *,
    jobs: int = 0,
    backend: MapBackend = "process",
    on_result: Callable[[R], None] | None = None,
) -> list[R]:
    """Map ``fn`` over ``items`` using sequential, thread, or process execution.

    Parallel backends return results in completion order. The sequential backend
    returns input order. ``jobs=0`` chooses a small automatic worker count.
    """
    work = list(items)
    if not work:
        return []

    if backend == "sequential":
        results: list[R] = []
        for item in work:
            result = fn(item)
            results.append(result)
            if on_result:
                on_result(result)
        return results

    worker_count = jobs if jobs > 0 else min(mp.cpu_count(), 8)
    executor_cls = ProcessPoolExecutor if backend == "process" else ThreadPoolExecutor

    results: list[R] = []
    with executor_cls(max_workers=worker_count) as pool:
        futures = [pool.submit(fn, item) for item in work]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            if on_result:
                on_result(result)
    return results
