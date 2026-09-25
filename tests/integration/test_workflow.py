"""Composition: CLI generation + indirect fixtures + markers + mock + capture."""

import json
import logging
from unittest.mock import Mock

import pytest

from pytest_power.client import announce_vlan
from pytest_power.network import TopologyError, attenuation, provision_verified

pytestmark = [pytest.mark.sdn, pytest.mark.regression]


@pytest.mark.smoke
@pytest.mark.parametrize("deployed_vlan", [100, 200], indirect=True, ids=lambda n: f"VLAN-{n}")
def test_full_lifecycle(controller, deployed_vlan, link_ports, monkeypatch, tmp_path, capsys, caplog):
    assert controller.reachable(deployed_vlan.vlan_id)
    assert deployed_vlan.ports == link_ports
    assert attenuation(15.0, 2.6) == pytest.approx(12.4, abs=0.1)

    # Replace only the external-style probe; state management remains real fake behavior.
    probe = Mock(return_value=False)
    monkeypatch.setattr(controller, "reachable", probe)
    with caplog.at_level(logging.INFO, logger="pytest_power.network"):
        with pytest.raises(TopologyError, match="unreachable"):
            provision_verified(controller, 300, link_ports)
    probe.assert_called_once_with(300)
    assert 300 not in controller.vlans  # The failed deployment rolled back.
    assert deployed_vlan.vlan_id in controller.vlans  # Existing deployment survived.
    assert "Deleted VLAN 300" in caplog.text

    capture = tmp_path / "controller.json"
    capture.write_text(json.dumps(controller.snapshot()), encoding="utf-8")
    assert str(deployed_vlan.vlan_id) in json.loads(capture.read_text(encoding="utf-8"))["vlans"]
    announce_vlan(deployed_vlan.vlan_id)
    assert capsys.readouterr().out == f"VLAN {deployed_vlan.vlan_id} ready\n"
    # deployed_vlan's yield finalizer deletes it after the test, including on failure.
