import json
import logging
from unittest.mock import Mock

import pytest

from pytest_power import client
from pytest_power.network import Vlan, provision_verified


def test_environment_override(monkeypatch):
    monkeypatch.setenv("CONTROLLER_IP", "lab.example.test")
    assert client.controller_address() == "lab.example.test"
    monkeypatch.delenv("CONTROLLER_IP")
    assert client.controller_address() == "controller.test"


def test_dictionary_override(monkeypatch, controller):
    with monkeypatch.context() as patch:
        patch.setitem(controller.ports, "eth1", False)
        assert controller.ports["eth1"] is False
    assert controller.ports["eth1"] is True


def test_method_override(monkeypatch, controller):
    check = Mock(return_value=True)
    monkeypatch.setattr(controller, "reachable", check)
    assert provision_verified(controller, 100, ("eth1", "eth2")) == Vlan(100, ("eth1", "eth2"))
    check.assert_called_once_with(100)


def test_temporary_config(tmp_path, topology_file):
    data = json.loads(topology_file.read_text(encoding="utf-8"))
    config = tmp_path / "switch.json"
    config.write_text(json.dumps({"ports": data["ports"], "vlan": 100}), encoding="utf-8")
    assert json.loads(config.read_text(encoding="utf-8"))["vlan"] == 100
    assert config.parent != topology_file.parent


def test_stdout(capsys):
    client.announce_vlan(100)
    captured = capsys.readouterr()
    assert captured.out == "VLAN 100 ready\n"
    assert captured.err == ""


def test_logging(caplog, controller):
    with caplog.at_level(logging.INFO, logger="pytest_power.network"):
        controller.create_vlan(100, ("eth1", "eth2"))
    assert caplog.record_tuples == [("pytest_power.network", logging.INFO, "Created VLAN 100 using OpenFlow 1.3")]


@pytest.mark.sdn
def test_request_metadata(request):
    assert request.node.name == "test_request_metadata"
    assert request.node.nodeid.endswith("::test_request_metadata")
    assert request.node.get_closest_marker("sdn") is not None
