import asyncio

import httpx
import pytest

from app.elexon import ElexonError, _get_rows


def test_transient_source_error_is_retried_once():
    attempts = []
    def handler(request):
        attempts.append(request)
        return httpx.Response(503) if len(attempts) == 1 else httpx.Response(200, json=[{"generation": 123}])
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://example.test") as client:
            return await _get_rows(client, "/dataset", {})
    assert asyncio.run(run()) == [{"generation": 123}]
    assert len(attempts) == 2


def test_malformed_source_payload_is_rejected():
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"unexpected": []})), base_url="https://example.test") as client:
            await _get_rows(client, "/dataset", {})
    with pytest.raises(ElexonError):
        asyncio.run(run())
