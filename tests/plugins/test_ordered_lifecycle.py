"""An intentionally stateful example; run the entire module in one process."""

import pytest

pytest.importorskip("pytest_order", reason="Install the plugins extra for ordering")
pytest.importorskip("pytest_dependency", reason="Install the plugins extra for dependencies")

from pytest_power.network import FakeController

pytestmark = pytest.mark.serial


@pytest.fixture(scope="module")
def device():
    instance = FakeController()
    yield instance
    # Resource cleanup is a fixture responsibility even if a step fails or skips.
    instance.close()


# Defined out of order to make the ordering plugin's effect visible.
@pytest.mark.order(2)
@pytest.mark.dependency(name="verified", depends=["created"])
def test_verify(device):
    assert device.reachable(100)


@pytest.mark.order(1)
@pytest.mark.dependency(name="created")
def test_create(device):
    assert device.create_vlan(100, ("eth1", "eth2")).vlan_id == 100


@pytest.mark.order(3)
@pytest.mark.dependency(depends=["verified"])
def test_remove(device):
    device.delete_vlan(100)
    assert device.vlans == {}
