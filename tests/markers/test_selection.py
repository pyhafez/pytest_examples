import sys

import pytest


@pytest.mark.smoke
@pytest.mark.sdn
def test_smoke(controller):
    assert controller.ports["eth1"]


@pytest.mark.regression
@pytest.mark.slow
def test_slow_category_is_just_metadata(controller):
    assert len(controller.ports) == 2


@pytest.mark.skip(reason="Example of an unconditionally retired test")
def test_retired_protocol():
    raise AssertionError("Skipped tests do not execute")


@pytest.mark.skipif(sys.platform != "linux", reason="Example Linux-only capability")
def test_linux_only():
    assert sys.platform == "linux"


@pytest.mark.hardware
def test_opt_in_simulated_hardware(controller):
    assert controller.create_vlan(200, ("eth1", "eth2")).vlan_id == 200


@pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="Fake controller lacks QinQ")
def test_known_unsupported_feature(controller):
    controller.create_qinq(100, 200)
