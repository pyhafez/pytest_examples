from unittest.mock import Mock

import pytest

pytest.importorskip("pytest_rerunfailures", reason="Install the plugins extra for retries")


@pytest.fixture(scope="module")
def transient_probe():
    # Module scope deliberately preserves the scripted sequence across reruns.
    # There is no random failure and no real network request.
    return Mock(side_effect=[TimeoutError("controller warming up"), True])


@pytest.mark.flaky(reruns=1, only_rerun="TimeoutError")
def test_one_transient_failure_then_success(transient_probe):
    assert transient_probe() is True
    assert transient_probe.call_count == 2
