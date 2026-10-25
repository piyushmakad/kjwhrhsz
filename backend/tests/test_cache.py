import asyncio

import pytest

from app.cache import AsyncTTLCache


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_concurrent_requests_share_one_load():
    calls = []

    async def load():
        calls.append(1)
        await asyncio.sleep(0.01)
        return "rows"

    async def run():
        cache = AsyncTTLCache(ttl_seconds=60, max_entries=4)
        return await asyncio.gather(*(cache.get_or_load("day", load) for _ in range(5)))

    assert asyncio.run(run()) == ["rows"] * 5
    assert len(calls) == 1


def test_entries_expire_after_ttl():
    clock = Clock()
    calls = []

    async def load():
        calls.append(1)
        return len(calls)

    async def run():
        cache = AsyncTTLCache(ttl_seconds=10, max_entries=4, clock=clock)
        first = await cache.get_or_load("day", load)
        clock.now = 9
        cached = await cache.get_or_load("day", load)
        clock.now = 11
        refreshed = await cache.get_or_load("day", load)
        return first, cached, refreshed

    assert asyncio.run(run()) == (1, 1, 2)


def test_failures_are_not_cached():
    attempts = []

    async def load():
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("upstream down")
        return "rows"

    async def run():
        cache = AsyncTTLCache(ttl_seconds=60, max_entries=4)
        with pytest.raises(RuntimeError):
            await cache.get_or_load("day", load)
        return await cache.get_or_load("day", load)

    assert asyncio.run(run()) == "rows"
    assert len(attempts) == 2


def test_least_recently_used_entry_is_evicted():
    loads = []

    async def run():
        cache = AsyncTTLCache(ttl_seconds=60, max_entries=2)

        def loader(key):
            async def load():
                loads.append(key)
                return key
            return load

        for key in ("a", "b", "a", "c", "a", "b"):
            await cache.get_or_load(key, loader(key))

    asyncio.run(run())
    assert loads == ["a", "b", "c", "b"]
