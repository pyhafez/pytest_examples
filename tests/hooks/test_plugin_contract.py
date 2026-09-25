"""pytester executes tiny isolated suites and asserts their observable behavior."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def sandbox(pytester, monkeypatch):
    # Subprocesses need the source path even when this repository isn't installed.
    source = str(Path(__file__).resolve().parents[2] / "src")
    monkeypatch.setenv("PYTHONPATH", source)
    # Keep optional third-party plugins out of these focused hook contracts.
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    pytester.makeconftest('pytest_plugins = ["pytest_power.pytest_plugin"]')
    return pytester


@pytest.mark.parametrize("phase", ["setup", "call", "teardown"])
def test_failure_reports_include_phase_and_controller(sandbox, phase):
    sandbox.makeconftest('''
        import pytest
        from pytest_power.network import FakeController
        pytest_plugins = ["pytest_power.pytest_plugin"]
        @pytest.fixture
        def controller():
            instance = FakeController()
            yield instance
            instance.close()
        @pytest.fixture
        def broken(controller):
            PHASE = %r
            if PHASE == "setup":
                raise RuntimeError("setup problem")
            yield
            if PHASE == "teardown":
                raise RuntimeError("teardown problem")
    ''' % phase)
    sandbox.makepyfile('''
        def test_problem(controller, broken):
            if %r == "call":
                controller.create_vlan(100, ("eth1", "eth2"))
                assert False, "call problem"
    ''' % phase)
    result = sandbox.runpytest_subprocess("-q")
    if phase == "call":
        result.assert_outcomes(failed=1)
    elif phase == "setup":
        result.assert_outcomes(errors=1)
    else:
        result.assert_outcomes(passed=1, errors=1)
    artifacts = list((sandbox.path / "artifacts").rglob("*.json"))
    assert len(artifacts) == 1
    payload = json.loads(artifacts[0].read_text(encoding="utf-8"))
    assert payload["phase"] == phase
    assert payload["outcome"] == "failed"
    assert payload["controller"] is not None
    assert "setup" in payload["lifecycle"]
    if phase == "call":
        assert "100" in payload["controller"]["vlans"]
        assert payload["controller"]["closed"] is False
    if phase == "teardown":
        assert "teardown" in payload["lifecycle"]


def test_yield_cleanup_runs_after_failure_in_reverse_order(sandbox):
    sandbox.makeconftest('''
        from pathlib import Path
        import pytest
        @pytest.fixture
        def bridge():
            yield "bridge"
            with Path("cleanup.txt").open("a") as output:
                output.write("bridge\\n")
        @pytest.fixture
        def vlan(bridge):
            yield "vlan"
            with Path("cleanup.txt").open("a") as output:
                output.write("vlan\\n")
    ''')
    sandbox.makepyfile('''
        def test_failure(vlan):
            raise RuntimeError("simulated test crash")
    ''')
    sandbox.runpytest_subprocess("-q").assert_outcomes(failed=1)
    assert (sandbox.path / "cleanup.txt").read_text().splitlines() == ["vlan", "bridge"]


def test_cleanup_before_yield_is_not_registered(sandbox):
    sandbox.makeconftest('''
        from pathlib import Path
        import pytest
        @pytest.fixture
        def bridge():
            yield
            Path("bridge-cleaned").touch()
        @pytest.fixture
        def broken(bridge):
            raise RuntimeError("setup failed before yield")
            yield
            Path("broken-cleaned").touch()
    ''')
    sandbox.makepyfile("def test_setup(broken): pass")
    sandbox.runpytest_subprocess("-q").assert_outcomes(errors=1)
    assert (sandbox.path / "bridge-cleaned").exists()
    assert not (sandbox.path / "broken-cleaned").exists()


def test_collection_moves_smoke_first(sandbox):
    sandbox.makepyfile('''
        import pytest
        def test_regular(): pass
        @pytest.mark.smoke
        def test_smoke(): pass
    ''')
    result = sandbox.runpytest_subprocess("--collect-only", "-q")
    nodes = [line for line in result.outlines if "::test_" in line]
    assert nodes[0].endswith("::test_smoke")
    assert nodes[1].endswith("::test_regular")


@pytest.mark.parametrize("enabled", [False, True])
def test_hardware_gate(sandbox, enabled):
    sandbox.makepyfile('''
        import pytest
        @pytest.mark.hardware
        def test_device(): assert True
    ''')
    args = ["-q", "--run-hardware"] if enabled else ["-q"]
    sandbox.runpytest_subprocess(*args).assert_outcomes(passed=int(enabled), skipped=int(not enabled))


def test_custom_json_collection(sandbox):
    cases = [{"name": "pair", "ports": ["p1", "p2"], "vlan_id": 1, "expected_ports": ["p1", "p2"]}]
    (sandbox.path / "test_lab.topology.json").write_text(json.dumps(cases), encoding="utf-8")
    sandbox.runpytest_subprocess("-q").assert_outcomes(passed=1)


@pytest.mark.parametrize("content", ["{", "{}", "[]", '[{"name": "missing-fields"}]'])
def test_invalid_json_fails_collection(sandbox, content):
    (sandbox.path / "test_bad.topology.json").write_text(content, encoding="utf-8")
    result = sandbox.runpytest_subprocess("-q")
    assert result.ret == pytest.ExitCode.INTERRUPTED
    result.assert_outcomes(errors=1)


def test_unwritable_artifact_location_keeps_original_failure(sandbox):
    (sandbox.path / "not-a-directory").write_text("a file", encoding="utf-8")
    sandbox.makepyfile('def test_failure(): assert False, "original failure"')
    result = sandbox.runpytest_subprocess("-q", "--artifacts-dir=not-a-directory")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*Cannot write failure diagnostics*"])
