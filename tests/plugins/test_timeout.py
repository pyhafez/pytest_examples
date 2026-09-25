from unittest.mock import Mock

import pytest

pytest.importorskip("pytest_timeout", reason="Install the plugins extra for deadlines")


@pytest.mark.timeout(5)
def test_mock_probe_completes_within_deadline():
    probe = Mock(return_value={"latency_ms": 2.5})
    assert probe()["latency_ms"] < 10
