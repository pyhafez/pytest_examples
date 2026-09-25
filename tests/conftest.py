"""Shared fixture chain. Only immutable configuration is session scoped."""

from dataclasses import dataclass
import json
from unittest.mock import create_autospec

import pytest

from pytest_power.network import FakeController


@dataclass
class FakeResource:
    name: str
    active: bool = True

    def close(self):
        self.active = False


@pytest.fixture(scope="session")
def network_bridge():
    """One simulated bridge per pytest process (per worker under xdist)."""
    bridge = FakeResource("bridge-test")
    yield bridge
    bridge.close()


@pytest.fixture(scope="session")
def docker_service(network_bridge):
    """A fake container depends on a bridge; neither touches Docker."""
    assert network_bridge.active
    service = FakeResource(f"controller-on-{network_bridge.name}")
    yield service
    service.close()


@pytest.fixture
def controller(docker_service, pytestconfig):
    assert docker_service.active
    instance = FakeController(
        address=pytestconfig.getoption("--controller-ip"),
        strict=pytestconfig.getoption("--emulation-mode") == "strict",
    )
    yield instance
    instance.close()


@pytest.fixture
def mock_controller():
    """An interaction mock, in contrast with controller's stateful fake."""
    return create_autospec(FakeController, instance=True, spec_set=True)


@pytest.fixture
def provisioned_vlan(controller):
    vlan = controller.create_vlan(100, ("eth1", "eth2"))
    yield vlan
    controller.delete_vlan(vlan.vlan_id)


@pytest.fixture(scope="session")
def topology_file(tmp_path_factory):
    path = tmp_path_factory.mktemp("topology") / "ports.json"
    path.write_text(json.dumps({"ports": ["eth1", "eth2"]}), encoding="utf-8")
    return path
