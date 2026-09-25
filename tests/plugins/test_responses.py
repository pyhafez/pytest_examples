import pytest

responses = pytest.importorskip("responses", reason="Install the plugins extra for requests interception")
requests = pytest.importorskip("requests")


@responses.activate
def test_requests_client_is_intercepted():
    responses.get("https://controller.test/ports", json={"ports": ["eth1"]})
    response = requests.get("https://controller.test/ports", timeout=1)
    response.raise_for_status()
    assert response.json() == {"ports": ["eth1"]}
    assert len(responses.calls) == 1
