import pytest

pytest.importorskip("pytest_mock", reason="Install the plugins extra for mocker")

from pytest_power.network import provision_verified


def test_spy_observes_real_behavior(mocker, controller):
    spy = mocker.spy(controller, "create_vlan")
    vlan = provision_verified(controller, 100, ("eth1", "eth2"))
    spy.assert_called_once_with(100, ("eth1", "eth2"), protocol="1.3")
    assert spy.spy_return == vlan
    assert controller.reachable(100)


def test_patch_replaces_behavior_and_restores_after_test(mocker, controller):
    probe = mocker.patch.object(controller, "reachable", side_effect=TimeoutError("SSH unavailable"))
    with pytest.raises(TimeoutError, match="SSH unavailable"):
        provision_verified(controller, 100, ("eth1", "eth2"))
    probe.assert_called_once_with(100)
    assert controller.vlans == {}
