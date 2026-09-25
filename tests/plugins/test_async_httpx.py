import pytest

pytest.importorskip("pytest_asyncio")
pytest.importorskip("pytest_httpx")
httpx = pytest.importorskip("httpx")

from pytest_power.client import fetch_ports_async


@pytest.mark.asyncio
async def test_async_http_interception(httpx_mock):
    """Combine the event-loop plugin with HTTP interception."""
    httpx_mock.add_response(url="https://controller.test/ports", json={"ports": ["leaf1"]})
    async with httpx.AsyncClient(base_url="https://controller.test") as client:
        assert await fetch_ports_async(client) == ["leaf1"]
