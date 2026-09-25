import pytest

pytest.importorskip("pytest_httpx", reason="Install the plugins extra for HTTPX interception")
httpx = pytest.importorskip("httpx")

from pytest_power.client import fetch_ports


def test_controller_api(httpx_mock):
    httpx_mock.add_response(method="GET", url="https://controller.test/ports", json={"ports": ["eth1", "eth2"]})
    with httpx.Client(base_url="https://controller.test") as client:
        assert fetch_ports(client) == ["eth1", "eth2"]
    assert httpx_mock.get_request().method == "GET"


def test_controller_api_failure(httpx_mock):
    httpx_mock.add_response(url="https://controller.test/ports", status_code=503)
    with httpx.Client(base_url="https://controller.test") as client:
        with pytest.raises(httpx.HTTPStatusError, match="503"):
            fetch_ports(client)
