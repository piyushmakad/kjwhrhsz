"""In-process cache for upstream fetches.

January 2026 source data is historical, so repeated requests for the same decision
date can reuse one Elexon fetch. Concurrent requests for a key share one in-flight
load, and failures are never cached.
"""

import asyncio
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Hashable
from typing import Generic, TypeVar

T = TypeVar("T")


class AsyncTTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float, max_entries: int, clock: Callable[[], float] = time.monotonic):
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._clock = clock
        self._values: OrderedDict[Hashable, tuple[float, T]] = OrderedDict()
        self._loading: dict[Hashable, asyncio.Task[T]] = {}

    async def get_or_load(self, key: Hashable, load: Callable[[], Awaitable[T]]) -> T:
        entry = self._values.get(key)
        if entry and entry[0] > self._clock():
            self._values.move_to_end(key)
            return entry[1]
        task = self._loading.get(key)
        if task is None:
            task = asyncio.ensure_future(load())
            self._loading[key] = task
            task.add_done_callback(lambda done: self._finish(key, done))
        return await asyncio.shield(task)

    def _finish(self, key: Hashable, task: asyncio.Task[T]) -> None:
        self._loading.pop(key, None)
        if task.cancelled() or task.exception() is not None:
            return
        self._values[key] = (self._clock() + self._ttl, task.result())
        self._values.move_to_end(key)
        while len(self._values) > self._max_entries:
            self._values.popitem(last=False)

    def clear(self) -> None:
        self._values.clear()
