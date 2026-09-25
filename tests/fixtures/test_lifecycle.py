"""Run with --setup-show to see setup order, caching and reverse teardown."""

import os

import pytest


@pytest.fixture(scope="module")
def module_config():
    return {"protocol": "1.3"}


@pytest.fixture(scope="class")
def class_ports(package_inventory):
    return tuple(f"{device}:eth1" for device in package_inventory)


def test_yield_fixture_composes_resources(controller, provisioned_vlan, network_bridge, docker_service):
    assert network_bridge.active and docker_service.active
    assert controller.reachable(provisioned_vlan.vlan_id)


def test_function_fixture_starts_clean(controller):
    assert controller.vlans == {}


def test_autouse_needs_no_signature_argument():
    assert os.environ["LAB_ENV"] == "test"


class TestScopeHierarchy:
    def test_class_fixture(self, class_ports, module_config, request):
        assert class_ports == ("leaf-1:eth1", "leaf-2:eth1")
        assert request.getfixturevalue("module_config") is module_config

    def test_class_fixture_again(self, class_ports, request):
        assert request.getfixturevalue("class_ports") is class_ports


def test_module_fixture(module_config):
    assert module_config["protocol"] == "1.3"
