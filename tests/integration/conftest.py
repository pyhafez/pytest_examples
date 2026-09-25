import pytest

from pytest_power.network import FakeController, provision_verified


def pytest_generate_tests(metafunc):
    """Generate test cases at collection time using the custom CLI option."""
    if "link_ports" in metafunc.fixturenames:
        topology = metafunc.config.getoption("--topo")
        links = [("eth1", "eth2")] if topology == "pair" else [("spine", "leaf1"), ("spine", "leaf2")]
        metafunc.parametrize("link_ports", links, ids=lambda ports: "-to-".join(ports))


@pytest.fixture
def controller(pytestconfig):
    """Locally override the shared fixture for this topology's ports."""
    ports = ("eth1", "eth2") if pytestconfig.getoption("--topo") == "pair" else ("spine", "leaf1", "leaf2")
    instance = FakeController(
        ports,
        address=pytestconfig.getoption("--controller-ip"),
        strict=pytestconfig.getoption("--emulation-mode") == "strict",
    )
    yield instance
    instance.close()


@pytest.fixture
def deployed_vlan(controller, request, link_ports):
    vlan = provision_verified(controller, request.param, link_ports, protocol="1.5")
    yield vlan
    controller.delete_vlan(vlan.vlan_id)
