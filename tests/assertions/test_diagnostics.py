import pytest

from pytest_power.network import TopologyError, Vlan, attenuation


def test_plain_asserts_on_structures_and_dataclasses(controller):
    vlan = controller.create_vlan(100, ("eth1", "eth2"))
    assert vlan == Vlan(100, ("eth1", "eth2"))
    assert {"ports": list(vlan.ports)} == {"ports": ["eth1", "eth2"]}
    assert set(controller.ports) == {"eth1", "eth2"}


def test_error_type_message_and_no_partial_write(controller):
    controller.ports["eth2"] = False
    with pytest.raises(TopologyError, match=r"^Port Down: eth2$") as error:
        controller.create_vlan(100, ("eth1", "eth2"))
    assert type(error.value) is TopologyError
    assert controller.vlans == {}


def test_warning(controller):
    with pytest.warns(DeprecationWarning, match=r"Use controller\.ports"):
        assert controller.legacy_port_names() == ["eth1", "eth2"]


def test_float_tolerance():
    assert attenuation(15.0, 2.6) == pytest.approx(12.4, abs=0.1)


@pytest.mark.diagnostic_demo
def test_intentional_failure(controller, provisioned_vlan):
    """Opt in to see rewritten assertions and a pre-teardown controller dump."""
    actual = controller.snapshot()
    expected = {"100": {"vlan_id": 100, "ports": ("eth1", "eth9"), "protocol": "1.3"}}
    assert actual["vlans"] == expected
