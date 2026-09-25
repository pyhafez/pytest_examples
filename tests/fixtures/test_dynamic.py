import pytest

from pytest_power.network import FakeController, TopologyError


@pytest.fixture
def memory_controller():
    controller = FakeController()
    yield controller
    controller.close()


@pytest.fixture
def strict_controller():
    controller = FakeController(strict=True)
    yield controller
    controller.close()


@pytest.fixture
def selected_controller(request):
    marker = request.node.get_closest_marker("backend")
    backend = marker.args[0] if marker else request.config.getoption("--emulation-mode")
    # Explicit mapping prevents arbitrary strings from resolving unintended fixtures.
    return request.getfixturevalue({"memory": "memory_controller", "strict": "strict_controller"}[backend])


def test_cli_selects_fixture(selected_controller, pytestconfig):
    assert selected_controller.strict == (pytestconfig.getoption("--emulation-mode") == "strict")


@pytest.mark.backend("strict")
def test_marker_overrides_cli(selected_controller):
    with pytest.raises(TopologyError, match="at least two ports"):
        selected_controller.create_vlan(10, ("eth1",))


@pytest.mark.backend("memory")
def test_memory_backend_allows_one_port(selected_controller):
    assert selected_controller.create_vlan(10, ("eth1",)).ports == ("eth1",)
