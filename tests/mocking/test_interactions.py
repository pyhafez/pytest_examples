"""Standard-library mocks work without installing pytest-mock."""

from unittest.mock import AsyncMock, Mock, call

import asyncio
import pytest

from pytest_power.client import fetch_ports_async
from pytest_power.network import TopologyError, Vlan, provision_verified


def test_autospec_records_collaborator_calls(mock_controller):
    expected = Vlan(100, ("eth1", "eth2"))
    mock_controller.create_vlan.return_value = expected
    mock_controller.reachable.return_value = True
    assert provision_verified(mock_controller, 100, expected.ports) is expected
    assert mock_controller.mock_calls == [
        call.create_vlan(100, ("eth1", "eth2"), protocol="1.3"),
        call.reachable(100),
    ]
    mock_controller.delete_vlan.assert_not_called()


@pytest.mark.parametrize("verification", [False, TimeoutError("probe timed out")], ids=["unreachable", "timeout"])
def test_failed_verification_rolls_back(mock_controller, verification):
    if isinstance(verification, Exception):
        mock_controller.reachable.side_effect = verification
        expected_error, message = TimeoutError, "probe timed out"
    else:
        mock_controller.reachable.return_value = verification
        expected_error, message = TopologyError, "unreachable"
    with pytest.raises(expected_error, match=message):
        provision_verified(mock_controller, 100, ("eth1", "eth2"))
    mock_controller.delete_vlan.assert_called_once_with(100)


def test_failed_creation_does_not_delete_existing_state(mock_controller):
    mock_controller.create_vlan.side_effect = TopologyError("already exists")
    with pytest.raises(TopologyError, match="already exists"):
        provision_verified(mock_controller, 100, ("eth1", "eth2"))
    mock_controller.delete_vlan.assert_not_called()
    mock_controller.reachable.assert_not_called()


def test_autospec_rejects_wrong_interface(mock_controller):
    with pytest.raises(AttributeError):
        mock_controller.creat_vlan(100)
    with pytest.raises(TypeError):
        mock_controller.create_vlan()


def test_asyncmock_without_an_async_plugin():
    response = Mock()
    response.json.return_value = {"ports": ["eth1", "eth2"]}
    client = Mock(get=AsyncMock(return_value=response))
    assert asyncio.run(fetch_ports_async(client)) == ["eth1", "eth2"]
    client.get.assert_awaited_once_with("/ports")
    response.raise_for_status.assert_called_once_with()
