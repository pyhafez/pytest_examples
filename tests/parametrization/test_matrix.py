import pytest

from pytest_power.network import FakeController, TopologyError, attenuation


@pytest.mark.sdn
@pytest.mark.parametrize("protocol", ["1.3", "1.5"], ids=lambda p: f"OpenFlow-{p}")
@pytest.mark.parametrize("vlan_id", [1, 100, 4094], ids=lambda n: f"VLAN-{n}")
def test_protocol_vlan_matrix(controller, protocol, vlan_id):
    """Stacking two decorators creates a 2 x 3 Cartesian product."""
    vlan = controller.create_vlan(vlan_id, ("eth1", "eth2"), protocol)
    assert vlan.protocol == protocol
    assert controller.reachable(vlan_id)


@pytest.fixture
def topology(request):
    """Indirect parameters arrive at the fixture through request.param."""
    controller = FakeController(request.param)
    yield controller
    controller.close()


@pytest.mark.parametrize(
    "topology, expected_count",
    [(('eth1', 'eth2'), 2), (('spine', 'leaf1', 'leaf2'), 3)],
    indirect=["topology"],
    ids=["pair", "spine-leaf"],
)
def test_indirect_topology(topology, expected_count):
    assert len(topology.ports) == expected_count


@pytest.mark.parametrize("vlan_id", [0, 4095, -1, True, "100"], ids=repr)
def test_invalid_vlan_ids(controller, vlan_id):
    with pytest.raises(TopologyError, match="between 1 and 4094"):
        controller.create_vlan(vlan_id, ("eth1", "eth2"))
    assert controller.vlans == {}


@pytest.fixture(params=["1.3", "1.5"], ids=lambda p: f"fixture-OpenFlow-{p}")
def protocol(request):
    return request.param


def test_fixture_parametrization(controller, protocol):
    assert controller.create_vlan(100, ("eth1", "eth2"), protocol).protocol == protocol


@pytest.mark.parametrize(
    "input_dbm, output_dbm, expected",
    [pytest.param(15.0, 2.6, 12.4, id="EDFA-Gain-15dBm", marks=pytest.mark.smoke)],
)
def test_named_optical_case(input_dbm, output_dbm, expected):
    assert attenuation(input_dbm, output_dbm) == pytest.approx(expected, abs=0.1)
