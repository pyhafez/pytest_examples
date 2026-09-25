from unittest.mock import AsyncMock, Mock

import pytest

pytest_asyncio = pytest.importorskip("pytest_asyncio", reason="Install the plugins extra for async fixtures")

from pytest_power.client import fetch_ports_async


@pytest_asyncio.fixture
async def async_client():
    response = Mock()
    response.json.return_value = {"ports": ["eth1", "eth2"]}
    client = Mock(get=AsyncMock(return_value=response), aclose=AsyncMock())
    yield client
    await client.aclose()
    client.aclose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_async_fixture_and_await_assertions(async_client):
    assert await fetch_ports_async(async_client) == ["eth1", "eth2"]
    async_client.get.assert_awaited_once_with("/ports")


@pytest.mark.asyncio
async def test_async_error(async_client):
    async_client.get.side_effect = TimeoutError("event stream unavailable")
    with pytest.raises(TimeoutError, match="event stream unavailable"):
        await fetch_ports_async(async_client)
